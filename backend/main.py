from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from rapidfuzz import process, fuzz
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent.parent

# Data files
SKILL_DEMAND_FILE = BASE_DIR / "data" / "processed" / "skill_demand.csv"
SKILL_TRENDS_FILE = BASE_DIR / "data" / "processed" / "skill_trends.csv"
ROLE_SKILL_FILE = BASE_DIR / "data" / "processed" / "role_skill_mapping.json"
SKILL_TAXONOMY_FILE = BASE_DIR / "data" / "processed" / "skill_taxonomy.json"
COMPANY_PROFILES_FILE = BASE_DIR / "data" / "processed" / "company_profiles.json"
COMPANY_RECS_FILE = BASE_DIR / "data" / "processed" / "company_recommendations_engine.json"
COMPANY_TRENDS_FILE = BASE_DIR / "data" / "processed" / "company_market_trends.json"
SALARY_MODEL_FILE = BASE_DIR / "models" / "salary_model.pkl"
SALARY_PREPROCESSOR_FILE = BASE_DIR / "models" / "salary_preprocessor.pkl"
SALARY_METADATA_FILE = BASE_DIR / "models" / "salary_model_metadata.json"

app = FastAPI(
    title="Career Compass API",
    description="Backend API for Career Compass ML system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Load data at startup
skill_demand = pd.read_csv(SKILL_DEMAND_FILE)
skill_trends = pd.read_csv(SKILL_TRENDS_FILE)

with open(ROLE_SKILL_FILE, "r") as f:
    role_skill_data = json.load(f)

with open(SKILL_TAXONOMY_FILE, "r") as f:
    skill_taxonomy = json.load(f)

with open(COMPANY_PROFILES_FILE, "r") as f:
    company_profiles = json.load(f)

with open(COMPANY_RECS_FILE, "r") as f:
    company_recs_data = json.load(f)

with open(COMPANY_TRENDS_FILE, "r") as f:
    company_trends = json.load(f)

# Load salary model
salary_model = joblib.load(SALARY_MODEL_FILE)
salary_preprocessor = joblib.load(SALARY_PREPROCESSOR_FILE)
with open(SALARY_METADATA_FILE, "r") as f:
    salary_metadata = json.load(f)

canonical_skills = skill_taxonomy["skills"]
skill_to_idx = {s: i for i, s in enumerate(canonical_skills)}
skill_demand_dict = skill_demand.set_index("skill").to_dict("index")
skill_trends_dict = skill_trends.set_index("skill").to_dict("index")
role_skill_mapping = role_skill_data["role_skill_mapping"]
category_skill_mapping = role_skill_data["category_skill_mapping"]

TREND_WEIGHTS = {"Rising": 1.5, "Stable": 1.0, "Declining": 0.5}


def dataframe_to_records(dataframe):
    clean_df = dataframe.astype(object).where(pd.notna(dataframe), None)
    return clean_df.to_dict(orient="records")


def normalize_skill(skill: str) -> str:
    match = process.extractOne(skill, canonical_skills, scorer=fuzz.ratio, score_cutoff=85)
    return match[0] if match else skill


def get_skill_priority_score(skill: str, role_context: Optional[str] = None) -> float:
    demand_info = skill_demand_dict.get(skill, {})
    trend_info = skill_trends_dict.get(skill, {})

    posting_count = demand_info.get("posting_count", 0)
    demand_share = demand_info.get("demand_share_pct", 0)
    avg_demand_score = demand_info.get("avg_demand_score", 0)

    trend = trend_info.get("trend", "Stable")
    trend_weight = TREND_WEIGHTS.get(trend, 1.0)

    max_postings = skill_demand["posting_count"].max()
    norm_posting_freq = posting_count / max_postings if max_postings > 0 else 0

    max_demand_share = skill_demand["demand_share_pct"].max()
    norm_demand_share = demand_share / max_demand_share if max_demand_share > 0 else 0

    norm_demand_score = min(avg_demand_score / 100.0, 1.0)

    role_relevance = 1.0
    if role_context and role_context in role_skill_mapping:
        role_skills = {s["skill"]: s["frequency"] for s in role_skill_mapping[role_context]["skills"]}
        max_freq = max(role_skills.values()) if role_skills else 1
        role_relevance = role_skills.get(skill, 0) / max_freq

    score = (
        0.30 * norm_posting_freq +
        0.20 * norm_demand_share +
        0.20 * norm_demand_score +
        0.20 * trend_weight +
        0.10 * role_relevance
    )
    return score


def get_skill_gap_recommendations(current_skills: List[str], target_role: Optional[str] = None, top_n: int = 15):
    current_normalized = set()
    for skill in current_skills:
        current_normalized.add(normalize_skill(skill))

    target_skills = set()
    if target_role and target_role in role_skill_mapping:
        target_skills = {s["skill"] for s in role_skill_mapping[target_role]["skills"]}
    else:
        target_skills = set(canonical_skills)

    missing_skills = target_skills - current_normalized

    recommendations = []
    for skill in missing_skills:
        priority_score = get_skill_priority_score(skill, target_role)
        demand_info = skill_demand_dict.get(skill, {})
        trend_info = skill_trends_dict.get(skill, {})

        reasons = []
        trend = trend_info.get("trend", "Stable")
        if trend == "Rising":
            reasons.append(f"Rising trend (slope: {trend_info.get('trend_slope', 0):.3f})")
        elif trend == "Declining":
            reasons.append(f"Declining trend (slope: {trend_info.get('trend_slope', 0):.3f})")
        else:
            reasons.append("Stable demand")

        posting_count = demand_info.get("posting_count", 0)
        reasons.append(f"Appears in {posting_count} postings")
        reasons.append(f"Demand score: {demand_info.get('avg_demand_score', 0):.1f}")

        if target_role and target_role in role_skill_mapping:
            role_skills = {s["skill"]: s["frequency"] for s in role_skill_mapping[target_role]["skills"]}
            if skill in role_skills:
                reasons.append(f"Required for target role ({role_skills[skill]} postings)")

        recommendations.append({
            "skill": skill,
            "priority_score": round(priority_score, 4),
            "trend": trend,
            "trend_slope": trend_info.get("trend_slope", 0),
            "posting_count": posting_count,
            "demand_share_pct": demand_info.get("demand_share_pct", 0),
            "avg_demand_score": demand_info.get("avg_demand_score", 0),
            "avg_demand_growth": demand_info.get("avg_demand_growth", 0),
            "avg_salary": demand_info.get("avg_salary", 0),
            "reasons": reasons,
            "role_relevant": skill in {s["skill"] for s in role_skill_mapping.get(target_role, {}).get("skills", [])}
        })

    recommendations.sort(key=lambda x: -x["priority_score"])
    return recommendations[:top_n]


def predict_salary(input_data: dict) -> dict:
    """Predict salary using the trained XGBoost model."""
    # Create feature vector matching training data
    feature_cols = salary_metadata["feature_columns"]
    categorical_cols = salary_metadata["categorical_columns"]
    numerical_cols = salary_metadata["numerical_columns"]
    top_skills = salary_metadata["top_skills"]

    # Build input row
    row = {}
    for col in feature_cols:
        if col in input_data:
            row[col] = input_data[col]
        elif col == "required_skills":
            row[col] = "|".join(input_data.get("skills", []))
        else:
            row[col] = None

    df = pd.DataFrame([row])

    # Add skill binary features
    for skill in top_skills:
        df[f"skill_{skill}"] = df["required_skills"].fillna("").apply(
            lambda x: 1 if skill in [s.strip() for s in x.split("|")] else 0
        )
    df = df.drop(columns=["required_skills"])

    # Fill missing
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")
    for col in numerical_cols:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median() if df[col].dtype in ["float64", "int64"] else 0)

    # Ensure all columns exist
    for col in categorical_cols + numerical_cols:
        if col not in df.columns:
            df[col] = "Unknown" if col in categorical_cols else 0

    # Transform and predict
    X_processed = salary_preprocessor.transform(df)
    prediction = salary_model.predict(X_processed)[0]

    return {
        "predicted_salary": round(float(prediction), 0),
        "salary_band": {
            "low": round(float(prediction) * 0.9, 0),
            "high": round(float(prediction) * 1.1, 0)
        },
        "model_info": {
            "model_type": salary_metadata["model_type"],
            "test_mae": salary_metadata["metrics"]["test_MAE"],
            "cv_mae": salary_metadata["metrics"]["cv_MAE"]
        }
    }


def recommend_companies(student_skills: List[str], target_salary: float = None, target_role: str = None, top_n: int = 10):
    student_vec = np.zeros(len(canonical_skills))
    for skill in student_skills:
        skill_norm = normalize_skill(skill)
        if skill_norm in skill_to_idx:
            idx = skill_to_idx[skill_norm]
            demand_share = skill_demand_dict.get(skill_norm, {}).get("demand_share_pct", 0)
            student_vec[idx] = 1 * (1 + demand_share / 100.0)

    norm = np.linalg.norm(student_vec)
    if norm > 0:
        student_vec = student_vec / norm

    similarities = []
    for company, data in company_recs_data["companies"].items():
        comp_vec = np.array(data["skill_vector"])
        sim = cosine_similarity([student_vec], [comp_vec])[0][0]

        salary_compat = 1.0
        if target_salary and data.get("avg_salary_midpoint"):
            company_sal = data["avg_salary_midpoint"]
            diff_pct = abs(target_salary - company_sal) / target_salary
            salary_compat = max(0, 1 - diff_pct / 0.2)

        trend_bonus = 1.0
        if data.get("hiring_trend") == "growing":
            trend_bonus = 1.2
        elif data.get("hiring_trend") == "contracting":
            trend_bonus = 0.8

        layoff_penalty = 1.0
        if data.get("has_layoffs"):
            layoff_penalty = 0.9
        if data.get("recent_layoff_events", 0) > 2:
            layoff_penalty = 0.7

        review_bonus = 1.0
        if data.get("avg_review_score"):
            review_bonus = 1 + (data["avg_review_score"] - 3) / 10

        combined_score = sim * salary_compat * trend_bonus * layoff_penalty * review_bonus

        role_relevance = 1.0
        if target_role and target_role in role_skill_mapping:
            role_skills = set(s["skill"] for s in role_skill_mapping[target_role]["skills"])
            company_skills = set(s["skill"] for s in data.get("top_skills", []))
            overlap = role_skills & company_skills
            if role_skills:
                role_relevance = 1 + len(overlap) / len(role_skills)

        combined_score *= role_relevance

        explanations = []
        if sim > 0.3:
            explanations.append(f"Strong skill match ({sim:.1%} similarity)")
        elif sim > 0.1:
            explanations.append(f"Moderate skill match ({sim:.1%} similarity)")
        else:
            explanations.append(f"Low skill match ({sim:.1%} similarity)")

        if target_salary and data.get("avg_salary_midpoint"):
            diff = target_salary - data["avg_salary_midpoint"]
            if abs(diff) / target_salary < 0.15:
                explanations.append(f"Salary aligned (${data['avg_salary_midpoint']:,.0f})")
            elif diff > 0:
                explanations.append(f"Below expectation by ${diff:,.0f}")
            else:
                explanations.append(f"Above expectation by ${abs(diff):,.0f}")

        if data.get("hiring_trend") == "growing":
            explanations.append("Hiring activity growing")
        elif data.get("hiring_trend") == "contracting":
            explanations.append("Hiring activity contracting")

        if data.get("has_layoffs"):
            explanations.append(f"Recent layoffs ({data.get('recent_layoff_events', 0)} events in 2026)")

        if data.get("avg_review_score"):
            explanations.append(f"Company rating: {data['avg_review_score']:.1f}/5")

        similarities.append({
            "company": company,
            "similarity_score": round(float(sim), 4),
            "combined_score": round(float(combined_score), 4),
            "skill_match_pct": round(float(sim) * 100, 1),
            "salary_compatibility": round(float(salary_compat), 2),
            "hiring_trend": data.get("hiring_trend", "unknown"),
            "has_layoffs": data.get("has_layoffs", False),
            "avg_review_score": data.get("avg_review_score"),
            "avg_salary_midpoint": data.get("avg_salary_midpoint"),
            "top_skills": [s["skill"] for s in data.get("top_skills", [])[:5]],
            "top_roles": [r["role"] for r in data.get("top_roles", [])[:3]],
            "total_postings": data.get("total_postings", 0),
            "explanations": explanations
        })

    similarities.sort(key=lambda x: -x["combined_score"])
    return similarities[:top_n]


def get_company_market_trend(company_name: str) -> dict:
    # Try exact match first
    if company_name in company_trends:
        return company_trends[company_name]

    # Try fuzzy match
    match = process.extractOne(company_name, list(company_trends.keys()), scorer=fuzz.ratio, score_cutoff=80)
    if match:
        return company_trends[match[0]]

    return None


# Request/Response models
class AnalyzeRequest(BaseModel):
    skills: List[str]
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    salary_expectation: Optional[float] = None


# API Endpoints
@app.get("/")
def root():
    return {"project": "Career Compass", "status": "running"}


@app.get("/api/skills")
def get_skills():
    return dataframe_to_records(skill_demand)


@app.get("/api/skills/{skill_name}")
def get_skill(skill_name: str):
    demand_match = skill_demand[skill_demand["skill"].str.lower() == skill_name.lower()]
    trend_match = skill_trends[skill_trends["skill"].str.lower() == skill_name.lower()]

    if demand_match.empty or trend_match.empty:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    demand = dataframe_to_records(demand_match)[0]
    trend = dataframe_to_records(trend_match)[0]

    return {"skill": demand["skill"], "demand": demand, "trend": trend}


@app.get("/api/trends")
def get_trends():
    return dataframe_to_records(skill_trends)


@app.get("/api/trends/{trend_type}")
def get_trends_by_type(trend_type: str):
    valid_types = ["Rising", "Stable", "Declining"]
    if trend_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Trend must be one of: {valid_types}")
    result = skill_trends[skill_trends["trend"] == trend_type]
    return dataframe_to_records(result)


@app.get("/api/roles")
def get_roles():
    roles = []
    for key, data in role_skill_mapping.items():
        roles.append({
            "role": data["role"],
            "category": data["category"],
            "key_skills": [s["skill"] for s in data["skills"][:10]],
            "total_postings": data["total_postings"]
        })
    return roles


@app.get("/api/categories")
def get_categories():
    return skill_taxonomy["categories"]


@app.get("/api/companies")
def get_companies():
    companies = []
    for name, profile in company_profiles.items():
        companies.append({
            "name": name,
            "total_postings": profile["total_postings"],
            "countries": profile["countries"],
            "top_skills": [s["skill"] for s in profile["top_skills"][:5]],
            "avg_review_score": profile.get("avg_review_score"),
            "has_layoffs": profile.get("has_layoffs", False)
        })
    return companies


@app.get("/api/companies/{company_name}")
def get_company(company_name: str):
    trend_data = get_company_market_trend(company_name)
    if not trend_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    profile = company_profiles.get(company_name, {})
    return {
        "company": company_name,
        "market_trend": trend_data,
        "profile": profile
    }


@app.get("/api/model/metrics")
def get_model_metrics():
    """Return salary prediction model evaluation metrics."""
    return {
        "model_type": salary_metadata["model_type"],
        "model_params": salary_metadata.get("model_params", {}),
        "metrics": salary_metadata["metrics"],
        "alternative_model_metrics": salary_metadata.get("alternative_model_metrics", {}),
        "feature_importance_top_20": _get_feature_importance(),
        "training_info": {
            "train_size": salary_metadata["train_size"],
            "test_size": salary_metadata["test_size"],
            "target": salary_metadata["target"],
            "note": salary_metadata["note"]
        }
    }


def _get_feature_importance():
    """Get feature importance from the trained model if available."""
    try:
        if hasattr(salary_model, 'feature_importances_'):
            importances = salary_model.feature_importances_
            feature_names = salary_metadata.get("feature_names_after_preprocessing", [])
            if feature_names and len(importances) == len(feature_names):
                feature_importance = list(zip(feature_names, importances))
                feature_importance.sort(key=lambda x: -x[1])
                return [{"feature": name, "importance": float(imp)} for name, imp in feature_importance[:20]]
    except Exception:
        pass
    return []


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    # Validate inputs
    if not request.skills:
        raise HTTPException(status_code=400, detail="At least one skill is required")

    # Normalize skills
    normalized_skills = [normalize_skill(s) for s in request.skills]

    # 1. Skill Gap Analysis
    skill_gap = get_skill_gap_recommendations(normalized_skills, request.target_role, top_n=15)

    # 2. Salary Prediction
    salary_input = {
        "skills": normalized_skills,
        "job_title": request.target_role.split("|")[-1] if request.target_role and "|" in request.target_role else request.target_role,
        "job_category": request.target_role.split("|")[0] if request.target_role and "|" in request.target_role else None,
        "experience_level": "Mid (3-5 yrs)",
        "country": "USA",
        "company_size": "Mid-size (501-5000)",
        "industry": "Technology",
        "years_of_experience": 4,
        "education_required": "Bachelor's",
        "remote_work": "Hybrid",
        "city": "San Francisco",
        "ai_salary_premium_pct": 10,
        "demand_score": 80,
        "demand_growth_yoy_pct": 20,
        "benefits_score_10": 7,
        "is_senior": 0,
        "is_remote_friendly": 1,
        "is_llm_role": 0,
        "skill_count": len(normalized_skills)
    }
    salary_prediction = predict_salary(salary_input)

    # 3. Company Recommendations
    company_recommendations = recommend_companies(
        normalized_skills,
        request.salary_expectation,
        request.target_role,
        top_n=10
    )

    # 4. Target Company Market Trend
    target_company_trend = None
    if request.target_company:
        target_company_trend = get_company_market_trend(request.target_company)

    # 5. Role Recommendations (bonus)
    role_recs = []
    current_normalized = set(normalized_skills)
    for role_key, role_data in role_skill_mapping.items():
        role_skills = {s["skill"]: s["frequency"] for s in role_data["skills"]}
        role_skill_set = set(role_skills.keys())
        overlap = current_normalized & role_skill_set
        if overlap:
            overlap_ratio = len(overlap) / len(role_skill_set)
            overlap_weight = sum(role_skills.get(s, 0) for s in overlap)
            total_weight = sum(role_skills.values())
            weight_ratio = overlap_weight / total_weight if total_weight > 0 else 0
            score = 0.6 * overlap_ratio + 0.4 * weight_ratio
            if score > 0:
                role_recs.append({
                    "role": role_data["role"],
                    "category": role_data["category"],
                    "match_score": round(score, 4),
                    "matching_skills": list(overlap),
                    "missing_skills": list(role_skill_set - current_normalized)[:8]
                })
    role_recs.sort(key=lambda x: -x["match_score"])
    role_recs = role_recs[:5]

    return {
        "career_summary": {
            "input_skills": normalized_skills,
            "target_role": request.target_role,
            "target_company": request.target_company,
            "salary_expectation": request.salary_expectation
        },
        "skill_gap_analysis": {
            "missing_skills_count": len(skill_gap),
            "recommendations": skill_gap
        },
        "salary_analysis": {
            "user_expectation": request.salary_expectation,
            "predicted_salary": salary_prediction["predicted_salary"],
            "salary_band": salary_prediction["salary_band"],
            "difference": round(request.salary_expectation - salary_prediction["predicted_salary"], 0) if request.salary_expectation else None,
            "model_info": salary_prediction["model_info"]
        },
        "company_recommendations": company_recommendations,
        "target_company_trend": target_company_trend,
        "role_recommendations": role_recs,
        "skill_trends_summary": {
            "rising": len([s for s in skill_gap if s["trend"] == "Rising"]),
            "stable": len([s for s in skill_gap if s["trend"] == "Stable"]),
            "declining": len([s for s in skill_gap if s["trend"] == "Declining"])
        }
    }
import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import process, fuzz

BASE_DIR = Path(__file__).resolve().parent.parent

COMPANY_PROFILES_FILE = BASE_DIR / "data" / "processed" / "company_profiles.json"
SKILL_TAXONOMY_FILE = BASE_DIR / "data" / "processed" / "skill_taxonomy.json"
SKILL_DEMAND_FILE = BASE_DIR / "data" / "processed" / "skill_demand.csv"
SKILL_TRENDS_FILE = BASE_DIR / "data" / "processed" / "skill_trends.csv"
ROLE_SKILL_FILE = BASE_DIR / "data" / "processed" / "role_skill_mapping.json"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "company_recommendations_engine.json"

# Load data
with open(COMPANY_PROFILES_FILE, "r") as f:
    company_profiles = json.load(f)

with open(SKILL_TAXONOMY_FILE, "r") as f:
    skill_taxonomy = json.load(f)

skill_demand = pd.read_csv(SKILL_DEMAND_FILE)
skill_trends = pd.read_csv(SKILL_TRENDS_FILE)

with open(ROLE_SKILL_FILE, "r") as f:
    role_skill_data = json.load(f)

canonical_skills = skill_taxonomy["skills"]
skill_to_idx = {s: i for i, s in enumerate(canonical_skills)}

# Create skill demand lookup
skill_demand_dict = skill_demand.set_index("skill").to_dict("index")
skill_trends_dict = skill_trends.set_index("skill").to_dict("index")

role_skill_mapping = role_skill_data["role_skill_mapping"]
category_skill_mapping = role_skill_data["category_skill_mapping"]

# Build company skill vectors
company_skill_vectors = {}
company_metadata = {}

for company, profile in company_profiles.items():
    # Create skill vector (TF-IDF weighted or simple count)
    skill_vec = np.zeros(len(canonical_skills))
    
    for skill_info in profile["top_skills"]:
        skill = skill_info["skill"]
        count = skill_info["count"]
        if skill in skill_to_idx:
            idx = skill_to_idx[skill]
            # Weight by demand share (TF-IDF style)
            demand_share = skill_demand_dict.get(skill, {}).get("demand_share_pct", 0)
            skill_vec[idx] = count * (1 + demand_share / 100.0)
    
    # Normalize
    norm = np.linalg.norm(skill_vec)
    if norm > 0:
        skill_vec = skill_vec / norm
    
    company_skill_vectors[company] = skill_vec
    company_metadata[company] = profile

# Save company skill vectors for fast lookup
company_vectors_data = {
    "canonical_skills": canonical_skills,
    "companies": {}
}

for company, vec in company_skill_vectors.items():
    meta = company_metadata[company]
    # Compute hiring trend (recent vs older postings)
    trend_months = meta.get("hiring_trend_monthly", [])
    recent_postings = 0
    older_postings = 0
    if trend_months:
        sorted_months = sorted(trend_months, key=lambda x: x["month"])
        mid = len(sorted_months) // 2
        for m in sorted_months[:mid]:
            older_postings += m["postings"]
        for m in sorted_months[mid:]:
            recent_postings += m["postings"]
    
    hiring_trend = "stable"
    if older_postings > 0:
        change = (recent_postings - older_postings) / older_postings
        if change > 0.2:
            hiring_trend = "growing"
        elif change < -0.2:
            hiring_trend = "contracting"
    
    # Average review score
    reviews = meta.get("reviews", [])
    avg_review = None
    if reviews:
        scores = [r["score"] for r in reviews if r.get("score") is not None]
        if scores:
            avg_review = np.mean(scores)
    
    # Layoff summary
    layoff_events = meta.get("layoff_events", [])
    total_laid_off = sum(e.get("laid_off", 0) for e in layoff_events if e.get("laid_off"))
    recent_layoffs = len([e for e in layoff_events if e.get("date") and str(e.get("date")).startswith("2026")])
    
    company_vectors_data["companies"][company] = {
        "skill_vector": vec.tolist(),
        "total_postings": meta.get("total_postings", 0),
        "top_skills": meta.get("top_skills", [])[:15],
        "top_roles": meta.get("top_roles", [])[:10],
        "avg_salary_midpoint": meta.get("avg_salary_midpoint"),
        "countries": meta.get("countries", []),
        "remote_friendly_pct": meta.get("remote_friendly_pct", 0),
        "hiring_trend": hiring_trend,
        "recent_postings": recent_postings,
        "older_postings": older_postings,
        "avg_review_score": avg_review,
        "has_layoffs": meta.get("has_layoffs", False),
        "total_laid_off": total_laid_off,
        "recent_layoff_events": recent_layoffs,
        "layoff_details": layoff_events[:5]  # Keep only recent 5
    }

with open(OUTPUT_FILE, "w") as f:
    json.dump(company_vectors_data, f, indent=2)

print(f"Saved company vectors to: {OUTPUT_FILE}")
print(f"Companies with vectors: {len(company_vectors_data['companies'])}")

# Test recommendation function
def recommend_companies(
    student_skills: list,
    target_salary: float = None,
    target_role: str = None,
    top_n: int = 10
) -> list:
    """
    Recommend companies based on skill similarity, salary compatibility, and hiring health.
    """
    # Build student skill vector
    student_vec = np.zeros(len(canonical_skills))
    for skill in student_skills:
        # Normalize skill name
        match = process.extractOne(skill, canonical_skills, scorer=fuzz.ratio, score_cutoff=85)
        if match:
            skill = match[0]
        if skill in skill_to_idx:
            idx = skill_to_idx[skill]
            demand_share = skill_demand_dict.get(skill, {}).get("demand_share_pct", 0)
            student_vec[idx] = 1 * (1 + demand_share / 100.0)
    
    # Normalize
    norm = np.linalg.norm(student_vec)
    if norm > 0:
        student_vec = student_vec / norm
    
    # Compute similarities
    similarities = []
    for company, data in company_vectors_data["companies"].items():
        comp_vec = np.array(data["skill_vector"])
        sim = cosine_similarity([student_vec], [comp_vec])[0][0]
        
        # Salary compatibility
        salary_compat = 1.0
        if target_salary and data.get("avg_salary_midpoint"):
            company_sal = data["avg_salary_midpoint"]
            # Within 20% is good compatibility
            diff_pct = abs(target_salary - company_sal) / target_salary
            salary_compat = max(0, 1 - diff_pct / 0.2)
        
        # Hiring trend bonus
        trend_bonus = 1.0
        if data.get("hiring_trend") == "growing":
            trend_bonus = 1.2
        elif data.get("hiring_trend") == "contracting":
            trend_bonus = 0.8
        
        # Layoff penalty
        layoff_penalty = 1.0
        if data.get("has_layoffs"):
            layoff_penalty = 0.9
        if data.get("recent_layoff_events", 0) > 2:
            layoff_penalty = 0.7
        
        # Review score bonus
        review_bonus = 1.0
        if data.get("avg_review_score"):
            review_bonus = 1 + (data["avg_review_score"] - 3) / 10  # 3.0 baseline
        
        # Combined score
        combined_score = sim * salary_compat * trend_bonus * layoff_penalty * review_bonus
        
        # Role relevance
        role_relevance = 1.0
        if target_role and target_role in role_skill_mapping:
            role_skills = set(s["skill"] for s in role_skill_mapping[target_role]["skills"])
            company_skills = set(s["skill"] for s in data.get("top_skills", []))
            overlap = role_skills & company_skills
            if role_skills:
                role_relevance = 1 + len(overlap) / len(role_skills)
        
        combined_score *= role_relevance
        
        # Build explanation
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
    
    # Sort by combined score
    similarities.sort(key=lambda x: -x["combined_score"])
    
    return similarities[:top_n]

# Test
if __name__ == "__main__":
    import pandas as pd
    
    test_skills = ["Python", "SQL", "Git", "AWS", "Docker"]
    target_salary = 180000
    target_role = "AI Engineering|AI Engineer"
    
    print(f"\nTesting company recommendations for skills: {test_skills}")
    print(f"Target salary: ${target_salary:,}")
    print(f"Target role: {target_role}")
    print()
    
    recs = recommend_companies(test_skills, target_salary, target_role, top_n=10)
    
    for i, rec in enumerate(recs, 1):
        print(f"{i}. {rec['company']} (score: {rec['combined_score']:.3f})")
        print(f"   Skill match: {rec['skill_match_pct']}% | Salary compat: {rec['salary_compatibility']:.2f} | Trend: {rec['hiring_trend']}")
        print(f"   Avg salary: ${rec['avg_salary_midpoint']:,.0f}" if rec['avg_salary_midpoint'] else "   Avg salary: N/A")
        print(f"   Layoffs: {'Yes' if rec['has_layoffs'] else 'No'} | Rating: {rec['avg_review_score']:.1f}" if rec['avg_review_score'] else "   Layoffs: No | Rating: N/A")
        print(f"   Top skills: {rec['top_skills']}")
        print(f"   Why: {'; '.join(rec['explanations'])}")
        print()
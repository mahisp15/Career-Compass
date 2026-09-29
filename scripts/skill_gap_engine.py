import pandas as pd
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent

SKILL_DEMAND_FILE = BASE_DIR / "data" / "processed" / "skill_demand.csv"
SKILL_TRENDS_FILE = BASE_DIR / "data" / "processed" / "skill_trends.csv"
ROLE_SKILL_FILE = BASE_DIR / "data" / "processed" / "role_skill_mapping.json"
SKILL_TAXONOMY_FILE = BASE_DIR / "data" / "processed" / "skill_taxonomy.json"

# Load data
skill_demand = pd.read_csv(SKILL_DEMAND_FILE)
skill_trends = pd.read_csv(SKILL_TRENDS_FILE)

with open(ROLE_SKILL_FILE, "r") as f:
    role_skill_data = json.load(f)

with open(SKILL_TAXONOMY_FILE, "r") as f:
    skill_taxonomy = json.load(f)

role_skill_mapping = role_skill_data["role_skill_mapping"]
category_skill_mapping = role_skill_data["category_skill_mapping"]
canonical_skills = set(skill_taxonomy["skills"])

# Create lookup dictionaries
skill_demand_dict = skill_demand.set_index("skill").to_dict("index")
skill_trends_dict = skill_trends.set_index("skill").to_dict("index")

# Trend weights
TREND_WEIGHTS = {
    "Rising": 1.5,
    "Stable": 1.0,
    "Declining": 0.5
}

def get_skill_priority_score(skill: str, role_context: Optional[str] = None) -> float:
    """
    Calculate a composite priority score for a skill.
    
    Components:
    - Normalized posting frequency (demand_share_pct)
    - Trend weight (Rising=1.5, Stable=1.0, Declining=0.5)
    - Demand score weight (avg_demand_score normalized)
    - Role relevance weight (if role_context provided)
    """
    # Get demand info
    demand_info = skill_demand_dict.get(skill, {})
    trend_info = skill_trends_dict.get(skill, {})
    
    posting_count = demand_info.get("posting_count", 0)
    demand_share = demand_info.get("demand_share_pct", 0)
    avg_demand_score = demand_info.get("avg_demand_score", 0)
    avg_demand_growth = demand_info.get("avg_demand_growth", 0)
    
    trend = trend_info.get("trend", "Stable")
    trend_slope = trend_info.get("trend_slope", 0)
    
    # Normalize posting frequency (0-1 scale based on max in dataset)
    max_postings = skill_demand["posting_count"].max()
    norm_posting_freq = posting_count / max_postings if max_postings > 0 else 0
    
    # Normalize demand share (0-1 scale)
    max_demand_share = skill_demand["demand_share_pct"].max()
    norm_demand_share = demand_share / max_demand_share if max_demand_share > 0 else 0
    
    # Normalize demand score (0-1 scale, assuming max ~100)
    norm_demand_score = min(avg_demand_score / 100.0, 1.0)
    
    # Trend weight
    trend_weight = TREND_WEIGHTS.get(trend, 1.0)
    
    # Role relevance (if provided)
    role_relevance = 1.0
    if role_context and role_context in role_skill_mapping:
        role_skills = {s["skill"]: s["frequency"] for s in role_skill_mapping[role_context]["skills"]}
        max_freq = max(role_skills.values()) if role_skills else 1
        role_relevance = role_skills.get(skill, 0) / max_freq
    elif role_context:
        # Try category-level
        for cat, data in category_skill_mapping.items():
            if role_context.startswith(cat):
                cat_skills = {s["skill"]: s["frequency"] for s in data["skills"]}
                max_freq = max(cat_skills.values()) if cat_skills else 1
                role_relevance = cat_skills.get(skill, 0) / max_freq
                break
    
    # Composite score
    # Weights: posting_freq(0.3) + demand_share(0.2) + demand_score(0.2) + trend(0.2) + role_relevance(0.1)
    score = (
        0.30 * norm_posting_freq +
        0.20 * norm_demand_share +
        0.20 * norm_demand_score +
        0.20 * trend_weight +
        0.10 * role_relevance
    )
    
    return score

def get_skill_gap_recommendations(
    current_skills: List[str],
    target_role: Optional[str] = None,
    target_category: Optional[str] = None,
    top_n: int = 15
) -> List[Dict[str, Any]]:
    """
    Get prioritized skill gap recommendations.
    
    Args:
        current_skills: List of skills the user already has
        target_role: Target role (e.g., "AI Engineering|AI Engineer")
        target_category: Target category (e.g., "AI Engineering")
        top_n: Number of recommendations to return
    
    Returns:
        List of recommended skills with priority scores and reasons
    """
    # Normalize current skills
    current_skills_normalized = set()
    for skill in current_skills:
        # Try to match to canonical
        from rapidfuzz import process, fuzz
        match = process.extractOne(skill, canonical_skills, scorer=fuzz.ratio, score_cutoff=85)
        if match:
            current_skills_normalized.add(match[0])
        else:
            current_skills_normalized.add(skill)
    
    # Determine target skills based on role or category
    target_skills = set()
    
    if target_role and target_role in role_skill_mapping:
        # Use role-specific skills
        for s in role_skill_mapping[target_role]["skills"]:
            target_skills.add(s["skill"])
    elif target_category and target_category in category_skill_mapping:
        # Use category-level skills
        for s in category_skill_mapping[target_category]["skills"]:
            target_skills.add(s["skill"])
    else:
        # Use all skills from demand data (fallback)
        target_skills = set(skill_demand["skill"].tolist())
    
    # Compute gap
    missing_skills = target_skills - current_skills_normalized
    
    # Score each missing skill
    recommendations = []
    for skill in missing_skills:
        priority_score = get_skill_priority_score(skill, target_role)
        
        demand_info = skill_demand_dict.get(skill, {})
        trend_info = skill_trends_dict.get(skill, {})
        
        # Build reason
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
        
        demand_score = demand_info.get("avg_demand_score", 0)
        reasons.append(f"Demand score: {demand_score:.1f}")
        
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
            "avg_demand_score": demand_score,
            "avg_demand_growth": demand_info.get("avg_demand_growth", 0),
            "avg_salary": demand_info.get("avg_salary", 0),
            "reasons": reasons,
            "role_relevant": skill in (role_skill_mapping.get(target_role, {}).get("skills", []) if target_role else [])
        })
    
    # Sort by priority score descending
    recommendations.sort(key=lambda x: -x["priority_score"])
    
    return recommendations[:top_n]

def get_role_recommendations(current_skills: List[str], top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Recommend roles based on current skill overlap.
    """
    current_skills_normalized = set()
    for skill in current_skills:
        from rapidfuzz import process, fuzz
        match = process.extractOne(skill, canonical_skills, scorer=fuzz.ratio, score_cutoff=85)
        if match:
            current_skills_normalized.add(match[0])
        else:
            current_skills_normalized.add(skill)
    
    role_scores = []
    for role_key, role_data in role_skill_mapping.items():
        role_skills = {s["skill"]: s["frequency"] for s in role_data["skills"]}
        role_skill_set = set(role_skills.keys())
        
        # Calculate overlap
        overlap = current_skills_normalized & role_skill_set
        overlap_count = len(overlap)
        total_role_skills = len(role_skill_set)
        
        if total_role_skills == 0:
            continue
        
        overlap_ratio = overlap_count / total_role_skills
        
        # Weight by posting frequency of overlapping skills
        overlap_weight = sum(role_skills.get(s, 0) for s in overlap)
        total_weight = sum(role_skills.values())
        weight_ratio = overlap_weight / total_weight if total_weight > 0 else 0
        
        # Combined score
        score = 0.6 * overlap_ratio + 0.4 * weight_ratio
        
        if score > 0:
            role_scores.append({
                "role": role_data["role"],
                "category": role_data["category"],
                "match_score": round(score, 4),
                "matching_skills": list(overlap),
                "missing_skills": list(role_skill_set - current_skills_normalized)[:10],
                "total_role_skills": total_role_skills,
                "overlap_count": overlap_count
            })
    
    role_scores.sort(key=lambda x: -x["match_score"])
    return role_scores[:top_n]

# Test the skill gap engine
if __name__ == "__main__":
    # Test with some sample skills
    test_skills = ["Python", "SQL", "Git"]
    target_role = "AI Engineering|AI Engineer"
    
    print(f"Testing skill gap for skills: {test_skills}")
    print(f"Target role: {target_role}")
    print()
    
    recommendations = get_skill_gap_recommendations(test_skills, target_role, top_n=10)
    
    print("Top 10 skill gap recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['skill']} (score: {rec['priority_score']})")
        print(f"   Trend: {rec['trend']}, Postings: {rec['posting_count']}, Demand Score: {rec['avg_demand_score']:.1f}")
        print(f"   Reasons: {'; '.join(rec['reasons'])}")
    
    print("\n\nTesting role recommendations:")
    role_recs = get_role_recommendations(test_skills, top_n=5)
    for i, rec in enumerate(role_recs, 1):
        print(f"\n{i}. {rec['category']} | {rec['role']} (score: {rec['match_score']})")
        print(f"   Matching: {rec['matching_skills'][:5]}")
        print(f"   Missing: {rec['missing_skills'][:5]}")
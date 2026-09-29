import pandas as pd
import json
from pathlib import Path
from collections import defaultdict
from rapidfuzz import process, fuzz

BASE_DIR = Path(__file__).resolve().parent.parent

JOBS_FILE = BASE_DIR / "data" / "processed" / "jobs_clean.csv"
COMPANY_REVIEWS_FILE = BASE_DIR / "data" / "processed" / "company_reviews_clean.csv"
LAYOFFS_FILE = BASE_DIR / "data" / "processed" / "layoffs_clean.csv"
SKILL_TAXONOMY_FILE = BASE_DIR / "data" / "processed" / "skill_taxonomy.json"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "company_profiles.json"

# Load canonical skills
with open(SKILL_TAXONOMY_FILE, "r") as f:
    skill_taxonomy = json.load(f)
canonical_skills = skill_taxonomy["skills"]

# Load datasets
jobs_df = pd.read_csv(JOBS_FILE)
reviews_df = pd.read_csv(COMPANY_REVIEWS_FILE)
layoffs_df = pd.read_csv(LAYOFFS_FILE)

print(f"Jobs: {jobs_df.shape}")
print(f"Reviews: {reviews_df.shape}")
print(f"Layoffs: {layoffs_df.shape}")

# Normalize company names - use employer_name from jobs and company from layoffs
# Let's see unique company names in each
print("\nTop companies in jobs_clean:")
print(jobs_df["employer_name"].value_counts().head(30))

print("\nTop companies in company_reviews_clean:")
print(reviews_df["employer_name"].value_counts().head(30))

print("\nTop companies in layoffs_clean:")
print(layoffs_df["Company"].value_counts().head(30))

# Build company profiles from jobs_clean
company_profiles = defaultdict(lambda: {
    "name": "",
    "postings": [],
    "skill_counts": defaultdict(int),
    "role_counts": defaultdict(int),
    "total_postings": 0,
    "avg_salary_min": None,
    "avg_salary_max": None,
    "avg_salary_midpoint": None,
    "countries": set(),
    "locations": set(),
    "remote_friendly": 0,
    "hiring_trend_monthly": defaultdict(int),
    "reviews": [],
    "avg_review_score": None,
    "layoff_events": [],
    "has_layoffs": False
})

# Process job postings
for _, row in jobs_df.iterrows():
    company = row["employer_name"]
    if pd.isna(company):
        continue
    
    profile = company_profiles[company]
    profile["name"] = company
    profile["total_postings"] += 1
    
    # Role
    role = row["job_title"]
    profile["role_counts"][role] += 1
    
    # Skills - need to extract from job_description
    # For now, we'll use a simple keyword-based approach
    # Later we can improve with NER or skill extraction
    
    # Salary
    if not pd.isna(row.get("job_min_salary")):
        if profile["avg_salary_min"] is None:
            profile["avg_salary_min"] = []
        profile["avg_salary_min"].append(row["job_min_salary"])
    
    if not pd.isna(row.get("job_max_salary")):
        if profile["avg_salary_max"] is None:
            profile["avg_salary_max"] = []
        profile["avg_salary_max"].append(row["job_max_salary"])
    
    if not pd.isna(row.get("salary_midpoint")):
        if profile["avg_salary_midpoint"] is None:
            profile["avg_salary_midpoint"] = []
        profile["avg_salary_midpoint"].append(row["salary_midpoint"])
    
    # Location
    if not pd.isna(row.get("job_country")):
        profile["countries"].add(row["job_country"])
    if not pd.isna(row.get("job_city")):
        profile["locations"].add(f"{row['job_city']}, {row['job_country']}")
    
    # Remote
    if row.get("job_is_remote") == True or row.get("job_is_remote") == "True":
        profile["remote_friendly"] += 1
    
    # Hiring trend by month
    if not pd.isna(row.get("posted_year")) and not pd.isna(row.get("posted_month")):
        month_key = f"{int(row['posted_year'])}-{int(row['posted_month']):02d}"
        profile["hiring_trend_monthly"][month_key] += 1

# Process reviews
for _, row in reviews_df.iterrows():
    company = row["employer_name"]
    if pd.isna(company):
        continue
    
    if company in company_profiles:
        profile = company_profiles[company]
        profile["reviews"].append({
            "publisher": row["publisher"],
            "score": row["normalized_score"],
            "review_count": row["review_count"]
        })

# Process layoffs
for _, row in layoffs_df.iterrows():
    company = row["Company"]
    if pd.isna(company):
        continue
    
    if company in company_profiles:
        profile = company_profiles[company]
        profile["has_layoffs"] = True
        profile["layoff_events"].append({
            "date": row["Date"] if not pd.isna(row["Date"]) else None,
            "laid_off": row["# Laid Off"] if not pd.isna(row["# Laid Off"]) else None,
            "percentage": row["layoff_percentage"] if not pd.isna(row["layoff_percentage"]) else None,
            "industry": row["Industry"] if not pd.isna(row["Industry"]) else None,
            "source": row["Source"] if not pd.isna(row["Source"]) else None,
            "stage": row["Stage"] if not pd.isna(row["Stage"]) else None
        })

# Compute aggregates and extract skills from job descriptions
def extract_skills_from_text(text, canonical_skills):
    """Extract skills from job description text using keyword matching"""
    if pd.isna(text):
        return []
    text_lower = text.lower()
    found_skills = []
    for skill in canonical_skills:
        # Simple substring matching - could be improved
        if skill.lower() in text_lower:
            found_skills.append(skill)
    return found_skills

print("\nExtracting skills from job descriptions...")
for company, profile in company_profiles.items():
    # Get postings for this company
    company_postings = jobs_df[jobs_df["employer_name"] == company]
    
    for _, row in company_postings.iterrows():
        skills = extract_skills_from_text(row["job_description"], canonical_skills)
        for skill in skills:
            profile["skill_counts"][skill] += 1

# Convert to serializable format
serializable_profiles = {}
for company, profile in company_profiles.items():
    # Compute average salaries
    avg_salary_min = None
    avg_salary_max = None
    avg_salary_midpoint = None
    
    if profile["avg_salary_min"] and len(profile["avg_salary_min"]) > 0:
        avg_salary_min = sum(profile["avg_salary_min"]) / len(profile["avg_salary_min"])
    if profile["avg_salary_max"] and len(profile["avg_salary_max"]) > 0:
        avg_salary_max = sum(profile["avg_salary_max"]) / len(profile["avg_salary_max"])
    if profile["avg_salary_midpoint"] and len(profile["avg_salary_midpoint"]) > 0:
        avg_salary_midpoint = sum(profile["avg_salary_midpoint"]) / len(profile["avg_salary_midpoint"])
    
    # Compute average review score
    avg_review_score = None
    if profile["reviews"]:
        scores = [r["score"] for r in profile["reviews"] if r["score"] is not None]
        if scores:
            avg_review_score = sum(scores) / len(scores)
    
    # Sort skill counts
    sorted_skills = sorted(profile["skill_counts"].items(), key=lambda x: -x[1])
    sorted_roles = sorted(profile["role_counts"].items(), key=lambda x: -x[1])
    
    # Sort hiring trend
    sorted_trend = sorted(profile["hiring_trend_monthly"].items())
    
    serializable_profiles[company] = {
        "name": company,
        "total_postings": profile["total_postings"],
        "top_skills": [{"skill": s, "count": c} for s, c in sorted_skills[:30]],
        "top_roles": [{"role": r, "count": c} for r, c in sorted_roles[:10]],
        "avg_salary_min": avg_salary_min,
        "avg_salary_max": avg_salary_max,
        "avg_salary_midpoint": avg_salary_midpoint,
        "countries": list(profile["countries"]),
        "locations": list(profile["locations"])[:10],
        "remote_friendly_pct": profile["remote_friendly"] / profile["total_postings"] if profile["total_postings"] > 0 else 0,
        "hiring_trend_monthly": [{"month": m, "postings": c} for m, c in sorted_trend],
        "reviews": profile["reviews"],
        "avg_review_score": avg_review_score,
        "layoff_events": profile["layoff_events"],
        "has_layoffs": profile["has_layoffs"]
    }

# Filter to companies with at least 2 postings
filtered_profiles = {k: v for k, v in serializable_profiles.items() if v["total_postings"] >= 2}

with open(OUTPUT_FILE, "w") as f:
    json.dump(filtered_profiles, f, indent=2)

print(f"\nSaved company profiles to: {OUTPUT_FILE}")
print(f"Companies with >=2 postings: {len(filtered_profiles)}")

# Print sample
for name, profile in list(filtered_profiles.items())[:5]:
    print(f"\n{name}:")
    print(f"  Postings: {profile['total_postings']}")
    print(f"  Top skills: {profile['top_skills'][:5]}")
    print(f"  Avg salary midpoint: {profile['avg_salary_midpoint']}")
    print(f"  Countries: {profile['countries']}")
    print(f"  Has layoffs: {profile['has_layoffs']}")
    print(f"  Avg review score: {profile['avg_review_score']}")
import pandas as pd
import json
from pathlib import Path
from collections import defaultdict
from rapidfuzz import process, fuzz

BASE_DIR = Path(__file__).resolve().parent.parent

AI_JOBS_FILE = BASE_DIR / "data" / "processed" / "ai_jobs_clean.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "role_skill_mapping.json"
SKILL_TAXONOMY_FILE = BASE_DIR / "data" / "processed" / "skill_taxonomy.json"

df = pd.read_csv(AI_JOBS_FILE)

print(f"Loaded dataset: {df.shape}")

# Get the canonical skill list from skill_demand.csv
skill_demand = pd.read_csv(BASE_DIR / "data" / "processed" / "skill_demand.csv")
canonical_skills = sorted(skill_demand["skill"].tolist())
print(f"Canonical skills: {len(canonical_skills)}")

# Build role-skill mapping
role_skill_counts = defaultdict(lambda: defaultdict(int))

for _, row in df.iterrows():
    role = row["job_title"]
    category = row["job_category"]
    skills_str = row["required_skills"]
    
    if pd.isna(skills_str):
        continue
    
    skills = [s.strip() for s in skills_str.split("|") if s.strip()]
    
    for skill in skills:
        # Normalize skill name using fuzzy matching to canonical list
        match = process.extractOne(skill, canonical_skills, scorer=fuzz.ratio, score_cutoff=90)
        if match:
            canonical_skill = match[0]
        else:
            canonical_skill = skill
        
        role_skill_counts[(category, role)][canonical_skill] += 1

# Convert to serializable format
role_skill_mapping = {}
for (category, role), skills in role_skill_counts.items():
    key = f"{category}|{role}"
    # Sort by frequency
    sorted_skills = sorted(skills.items(), key=lambda x: -x[1])
    role_skill_mapping[key] = {
        "category": category,
        "role": role,
        "skills": [{"skill": s, "frequency": c} for s, c in sorted_skills],
        "total_postings": sum(skills.values())
    }

# Also create role-level aggregated skills (across all roles in a category)
category_skills = defaultdict(lambda: defaultdict(int))
for (category, role), skills in role_skill_counts.items():
    for skill, count in skills.items():
        category_skills[category][skill] += count

category_skill_mapping = {}
for category, skills in category_skills.items():
    sorted_skills = sorted(skills.items(), key=lambda x: -x[1])
    category_skill_mapping[category] = {
        "category": category,
        "skills": [{"skill": s, "frequency": c} for s, c in sorted_skills],
        "total_postings": sum(skills.values())
    }

# Save skill taxonomy
skill_taxonomy = {
    "skills": canonical_skills,
    "categories": sorted(df["job_category"].unique().tolist()),
    "roles": sorted(df["job_title"].unique().tolist()),
    "experience_levels": sorted(df["experience_level"].unique().tolist()),
    "countries": sorted(df["country"].unique().tolist()),
    "company_sizes": sorted(df["company_size"].unique().tolist()),
    "industries": sorted(df["industry"].unique().tolist())
}

with open(SKILL_TAXONOMY_FILE, "w") as f:
    json.dump(skill_taxonomy, f, indent=2)

# Save role-skill mapping
output = {
    "role_skill_mapping": role_skill_mapping,
    "category_skill_mapping": category_skill_mapping,
    "metadata": {
        "source": "ai_jobs_clean.csv",
        "num_roles": len(role_skill_mapping),
        "num_categories": len(category_skill_mapping),
        "num_canonical_skills": len(canonical_skills)
    }
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nSaved role-skill mapping to: {OUTPUT_FILE}")
print(f"Saved skill taxonomy to: {SKILL_TAXONOMY_FILE}")
print(f"Roles mapped: {len(role_skill_mapping)}")
print(f"Categories mapped: {len(category_skill_mapping)}")

# Print sample
print("\nSample role-skill mapping (AI Engineering | AI Engineer):")
key = "AI Engineering|AI Engineer"
if key in role_skill_mapping:
    for s in role_skill_mapping[key]["skills"][:10]:
        print(f"  {s['skill']}: {s['frequency']}")
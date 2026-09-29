import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "ai_jobs_clean.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "skill_demand.csv"

df = pd.read_csv(INPUT_FILE)

print(f"Loaded dataset: {df.shape}")

df["required_skills"] = df["required_skills"].fillna("")

rows = []

for _, row in df.iterrows():
    skills = row["required_skills"].split("|")

    for skill in skills:
        skill = skill.strip()

        if not skill:
            continue

        rows.append({
            "skill": skill,
            "job_category": row["job_category"],
            "job_title": row["job_title"],
            "experience_level": row["experience_level"],
            "posting_year": row["posting_year"],
            "posting_month": row["posting_month"],
            "salary_midpoint": row["salary_midpoint"],
            "demand_score": row["demand_score"],
            "demand_growth_yoy_pct": row["demand_growth_yoy_pct"]
        })

skills_df = pd.DataFrame(rows)

print(f"Skill-level records: {skills_df.shape}")

skill_summary = (
    skills_df
    .groupby("skill")
    .agg(
        posting_count=("skill", "size"),
        avg_salary=("salary_midpoint", "mean"),
        avg_demand_score=("demand_score", "mean"),
        avg_demand_growth=("demand_growth_yoy_pct", "mean")
    )
    .reset_index()
)

skill_summary["demand_share_pct"] = (
    skill_summary["posting_count"]
    / len(df)
    * 100
)

skill_summary["demand_rank"] = (
    skill_summary["posting_count"]
    .rank(method="dense", ascending=False)
    .astype(int)
)

skill_summary = skill_summary.sort_values(
    "posting_count",
    ascending=False
)

skill_summary.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nSkill dataset created!")
print(f"Unique skills: {len(skill_summary)}")
print(f"Saved to: {OUTPUT_FILE}")

print("\nTop 20 skills:")
print(skill_summary.head(20).to_string(index=False))
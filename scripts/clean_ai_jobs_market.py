import pandas as pd
import re
from pathlib import Path

# PATHS
BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "raw" / "ai_jobs_market_2025_2026.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "ai_jobs_clean.csv"

# Create processed directory if it doesn't exist
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


# LOAD DATA
print("Loading dataset...")

df = pd.read_csv(INPUT_FILE)

print(f"Original shape: {df.shape}")


# 1. REMOVE DUPLICATES
before = len(df)

df = df.drop_duplicates(subset="job_id")

print(f"Removed duplicates: {before - len(df)}")


# 2. CLEAN TEXT COLUMNS
text_columns = [
    "job_title",
    "job_category",
    "experience_level",
    "education_required",
    "city",
    "country",
    "remote_work",
    "company_size",
    "industry",
    "salary_tier"
]

for col in text_columns:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )


# 3. CLEAN REQUIRED SKILLS
def clean_skills(skill_string):
    if pd.isna(skill_string):
        return ""

    skills = skill_string.split("|")

    cleaned = []

    for skill in skills:
        skill = skill.strip()

        if skill:
            cleaned.append(skill)

    # Remove duplicates while preserving order
    cleaned = list(dict.fromkeys(cleaned))

    return "|".join(cleaned)


df["required_skills"] = df["required_skills"].apply(clean_skills)


# 4. CREATE SKILL COUNT
df["skill_count"] = df["required_skills"].apply(
    lambda x: len(x.split("|")) if x else 0
)


# 5. NUMERICAL VALIDATION

# Experience cannot be negative
df.loc[df["years_of_experience"] < 0, "years_of_experience"] = pd.NA

# Salary cannot be negative
salary_columns = [
    "annual_salary_usd",
    "salary_min_usd",
    "salary_max_usd"
]

for col in salary_columns:
    df.loc[df[col] < 0, col] = pd.NA


# 6. SALARY VALIDATION

# Remove logically invalid salary ranges
invalid_salary = df["salary_max_usd"] < df["salary_min_usd"]

df.loc[invalid_salary, ["salary_min_usd", "salary_max_usd"]] = pd.NA


# 7. CREATE SALARY FEATURES

df["salary_midpoint"] = (
    df["salary_min_usd"] + df["salary_max_usd"]
) / 2

df["salary_range"] = (
    df["salary_max_usd"] - df["salary_min_usd"]
)


# 8. CREATE POSTING DATE

df["posting_date"] = pd.to_datetime(
    df["posting_year"].astype(str)
    + "-"
    + df["posting_month"].astype(str)
    + "-01",
    errors="coerce"
)


# 9. VALIDATE DEMAND / BENEFITS

# Demand score expected to be 0–100
df.loc[
    (df["demand_score"] < 0) |
    (df["demand_score"] > 100),
    "demand_score"
] = pd.NA

# Benefits score expected to be 0–10
df.loc[
    (df["benefits_score_10"] < 0) |
    (df["benefits_score_10"] > 10),
    "benefits_score_10"
] = pd.NA


# 10. RESET INDEX
df = df.reset_index(drop=True)


# 11. SAVE
df.to_csv(OUTPUT_FILE, index=False)


# REPORT
print("\nCleaning completed!")
print(f"Final shape: {df.shape}")
print(f"Saved to: {OUTPUT_FILE}")

print("\nMissing values after cleaning:")
print(df.isnull().sum())

print("\nFirst 5 rows:")
print(df.head())
import pandas as pd
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "raw" / "jobs.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "jobs_clean.csv"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Load dataset
print("Loading jobs dataset...")

df = pd.read_csv(INPUT_FILE)

print(f"Original shape: {df.shape}")

# Remove duplicates
before = len(df)

df = df.drop_duplicates(subset="job_id")

print(f"Removed duplicate jobs: {before - len(df)}")

# Clean text columns
text_columns = [
    "job_title",
    "employer_name",
    "job_publisher",
    "job_employment_type",
    "job_location",
    "job_city",
    "job_state",
    "job_country"
]

for col in text_columns:
    if col in df.columns:
        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )

# Clean company names
def clean_company_name(name):
    name = str(name).strip()

    if not name:
        return ""

    name = re.sub(r"\s+", " ", name)

    return name

df["employer_name"] = df["employer_name"].apply(clean_company_name)

# Clean job titles
df["job_title"] = (
    df["job_title"]
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)

# Clean job descriptions
def clean_description(text):
    if pd.isna(text):
        return ""

    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()

df["job_description"] = df["job_description"].apply(
    clean_description
)

# Convert posting date
df["job_posted_at_datetime_utc"] = pd.to_datetime(
    df["job_posted_at_datetime_utc"],
    errors="coerce"
)

df["posted_year"] = df["job_posted_at_datetime_utc"].dt.year
df["posted_month"] = df["job_posted_at_datetime_utc"].dt.month

# Clean salary values
salary_columns = [
    "job_salary",
    "job_min_salary",
    "job_max_salary"
]

for col in salary_columns:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

    df.loc[df[col] < 0, col] = pd.NA

# Validate salary range
invalid_salary = (
    df["job_max_salary"].notna()
    & df["job_min_salary"].notna()
    & (df["job_max_salary"] < df["job_min_salary"])
)

df.loc[
    invalid_salary,
    ["job_min_salary", "job_max_salary"]
] = pd.NA

# Create salary features
df["salary_midpoint"] = (
    df["job_min_salary"] +
    df["job_max_salary"]
) / 2

df["salary_range"] = (
    df["job_max_salary"] -
    df["job_min_salary"]
)

# Normalize remote field
df["job_is_remote"] = (
    df["job_is_remote"]
    .fillna(False)
    .astype(bool)
)

# Create description length
df["description_length"] = df["job_description"].str.len()

df = df.reset_index(drop=True)

# Save cleaned dataset
df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nCleaning completed!")
print(f"Final shape: {df.shape}")
print(f"Saved to: {OUTPUT_FILE}")

print("\nMissing values:")
print(df.isnull().sum())

print("\nFirst 5 rows:")
print(df.head())
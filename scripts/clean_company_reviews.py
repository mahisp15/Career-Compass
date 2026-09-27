import pandas as pd
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "raw" / "company_reviews.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "company_reviews_clean.csv"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Load dataset
print("Loading company reviews dataset...")

df = pd.read_csv(INPUT_FILE)

print(f"Original shape: {df.shape}")

# Remove duplicates
before = len(df)

df = df.drop_duplicates()

print(f"Removed duplicate rows: {before - len(df)}")

# Clean text columns
text_columns = [
    "publisher",
    "employer_name"
]

for col in text_columns:
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

df["employer_name"] = df["employer_name"].apply(
    clean_company_name
)

# Convert numerical columns
numeric_columns = [
    "score",
    "num_stars",
    "review_count",
    "max_score"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

# Validate ratings
df.loc[
    df["score"] < 0,
    "score"
] = pd.NA

df.loc[
    df["num_stars"] < 0,
    "num_stars"
] = pd.NA

df.loc[
    df["review_count"] < 0,
    "review_count"
] = pd.NA

# Normalize score to a 5-point scale
df["normalized_score"] = (
    df["score"] / df["max_score"]
) * 5

# Validate normalized score
df.loc[
    (df["normalized_score"] < 0) |
    (df["normalized_score"] > 5),
    "normalized_score"
] = pd.NA

# Reset index
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
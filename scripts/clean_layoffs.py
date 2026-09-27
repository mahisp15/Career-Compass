import pandas as pd
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "raw" / "layoffs.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "layoffs_clean.csv"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Load dataset
print("Loading layoffs dataset...")

df = pd.read_csv(INPUT_FILE)

print(f"Original shape: {df.shape}")

# Remove duplicates
before = len(df)

df = df.drop_duplicates()

print(f"Removed duplicate rows: {before - len(df)}")

# Clean text columns
text_columns = [
    "Company",
    "Location HQ",
    "Industry",
    "Source",
    "Stage"
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

df["Company"] = df["Company"].apply(clean_company_name)

# Convert date
df["Date"] = pd.to_datetime(
    df["Date"],
    errors="coerce"
)

df["layoff_year"] = df["Date"].dt.year
df["layoff_month"] = df["Date"].dt.month

# Clean number of employees laid off
df["# Laid Off"] = pd.to_numeric(
    df["# Laid Off"],
    errors="coerce"
)

df.loc[df["# Laid Off"] < 0, "# Laid Off"] = pd.NA

# Clean layoff percentage
def clean_percentage(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if not value:
        return pd.NA

    value = value.replace("%", "")

    try:
        return float(value)
    except ValueError:
        return pd.NA

df["layoff_percentage"] = df["%"].apply(
    clean_percentage
)

# Validate percentage
df.loc[
    (df["layoff_percentage"] < 0) |
    (df["layoff_percentage"] > 100),
    "layoff_percentage"
] = pd.NA

# Create useful company-level indicators
df["has_layoff_count"] = df["# Laid Off"].notna()
df["has_layoff_percentage"] = df["layoff_percentage"].notna()

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
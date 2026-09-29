import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "skill_trends.csv"

df = pd.read_csv(INPUT_FILE)

print("Trend dataset:")
print(df.shape)

print("\nTrend distribution:")
print(df["trend"].value_counts())

print("\nSlope statistics:")
print(df["trend_slope"].describe())

print("\nPercentage change statistics:")
print(df["percentage_change"].describe())

print("\nR-squared statistics:")
print(df["trend_r_squared"].describe())

columns = [
    "skill",
    "trend_slope",
    "trend_r_squared",
    "trend_p_value",
    "percentage_change",
    "total_postings"
]

print("\nRising skills:")
print(
    df[df["trend"] == "Rising"]
    .sort_values("trend_slope", ascending=False)[columns]
    .to_string(index=False)
)

print("\nDeclining skills:")
print(
    df[df["trend"] == "Declining"]
    .sort_values("trend_slope")[columns]
    .to_string(index=False)
)

print("\nStable skills:")
print(
    df[df["trend"] == "Stable"]
    .sort_values("total_postings", ascending=False)[columns]
    .head(15)
    .to_string(index=False)
)
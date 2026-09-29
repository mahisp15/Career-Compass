import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "ai_jobs_clean.csv"

df = pd.read_csv(INPUT_FILE)

print("Posting year distribution:")
print(df["posting_year"].value_counts().sort_index())

print("\nPosting month distribution:")
print(df["posting_month"].value_counts().sort_index())

print("\nYear-month distribution:")
print(
    df.groupby(
        ["posting_year", "posting_month"]
    )
    .size()
    .reset_index(name="job_postings")
    .sort_values(["posting_year", "posting_month"])
    .to_string(index=False)
)
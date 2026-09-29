import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import linregress

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "ai_jobs_clean.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "skill_trends.csv"

df = pd.read_csv(INPUT_FILE)

print(f"Loaded dataset: {df.shape}")

df["required_skills"] = df["required_skills"].fillna("")

df["period"] = (
    df["posting_year"].astype(str)
    + "-"
    + df["posting_month"].astype(str).str.zfill(2)
)

df["period"] = pd.to_datetime(
    df["period"],
    format="%Y-%m"
)

all_periods = pd.date_range(
    df["period"].min(),
    df["period"].max(),
    freq="MS"
)

monthly_total = (
    df.groupby("period")
    .size()
    .reindex(all_periods, fill_value=0)
)

rows = []

for _, row in df.iterrows():
    skills = row["required_skills"].split("|")

    for skill in skills:
        skill = skill.strip()

        if skill:
            rows.append({
                "skill": skill,
                "period": row["period"]
            })

skill_df = pd.DataFrame(rows)

print(f"Skill-level records: {len(skill_df)}")

monthly_skill = (
    skill_df
    .groupby(["skill", "period"])
    .size()
    .reset_index(name="skill_postings")
)

skills = sorted(
    skill_df["skill"].unique()
)

print(f"Unique skills found: {len(skills)}")

results = []

for skill in skills:
    skill_monthly = (
        monthly_skill[
            monthly_skill["skill"] == skill
        ]
        .set_index("period")["skill_postings"]
        .reindex(
            all_periods,
            fill_value=0
        )
    )

    demand_share = (
        skill_monthly / monthly_total
    ) * 100

    x = np.arange(len(demand_share))
    y = demand_share.values

    slope, intercept, r_value, p_value, std_err = linregress(
        x,
        y
    )

    first_value = demand_share.iloc[0]
    last_value = demand_share.iloc[-1]

    if first_value > 0:
        percentage_change = (
            (last_value - first_value)
            / first_value
        ) * 100
    else:
        percentage_change = np.nan

    if slope > 0.10:
        trend = "Rising"
    elif slope < -0.10:
        trend = "Declining"
    else:
        trend = "Stable"

    results.append({
        "skill": skill,
        "trend": trend,
        "trend_slope": slope,
        "trend_p_value": p_value,
        "trend_r_squared": r_value ** 2,
        "first_month_demand_pct": first_value,
        "last_month_demand_pct": last_value,
        "percentage_change": percentage_change,
        "total_postings": int(skill_monthly.sum())
    })

trend_df = pd.DataFrame(results)

trend_df = trend_df.sort_values(
    ["trend", "total_postings"],
    ascending=[True, False]
)

trend_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nSkill trend dataset created!")
print(f"Unique skills: {len(trend_df)}")
print(f"Saved to: {OUTPUT_FILE}")

print("\nTrend distribution:")
print(
    trend_df["trend"].value_counts()
)

print("\nTop skills by trend:")
print(
    trend_df[
        [
            "skill",
            "trend",
            "trend_slope",
            "trend_p_value",
            "percentage_change",
            "total_postings"
        ]
    ]
    .sort_values(
        "total_postings",
        ascending=False
    )
    .head(20)
    .to_string(index=False)
)
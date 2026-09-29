"""
CareerCompass - AI Jobs Market 2025-2026 Dataset Exploratory Data Analysis (Phase 3)

This script performs exploratory data analysis ONLY on data/raw/ai_jobs_market_2025_2026.csv.
It prints dataset metrics, column details, skill frequency, grouped aggregations,
generates distribution and comparison plots in reports/eda/, and outputs factual key dataset insights.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def setup_environment():
    """Ensure UTF-8 stdout encoding and configure plotting styles."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sns.set_theme(style="whitegrid", palette="muted")
    plt.rcParams.update({"figure.autolayout": True})


def get_paths() -> tuple[Path, Path]:
    """Resolves raw dataset path and report output directory."""
    base_dir = Path(__file__).resolve().parent.parent
    data_file = base_dir / "data" / "raw" / "ai_jobs_market_2025_2026.csv"
    output_dir = base_dir / "reports" / "eda"
    output_dir.mkdir(parents=True, exist_ok=True)
    return data_file, output_dir


def print_section(title: str):
    """Utility to print clear section headers."""
    print("\n" + "=" * 80)
    print(f" {title.upper()} ")
    print("=" * 80)


def analyze_overview(df: pd.DataFrame):
    """Prints dataset shape, column names, data types, duplicates, and missing values."""
    print_section("1. Dataset Overview")
    print(f"Dataset Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print(f"Duplicate Rows: {df.duplicated().sum():,}")

    overview_df = pd.DataFrame({
        "Column Name": df.columns,
        "Data Type": [str(dt) for dt in df.dtypes],
        "Missing Count": df.isnull().sum().values,
        "Missing (%)": (df.isnull().sum() / len(df) * 100).round(2).values,
    })
    print("\nColumn Summary:")
    print(overview_df.to_string(index=False))


def analyze_categorical_columns(df: pd.DataFrame):
    """Prints unique count and top 15 most frequent values for all categorical columns."""
    print_section("2. Categorical / Text Columns Analysis")
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    for col in cat_cols:
        print(f"\n--- Column: '{col}' ---")
        print(f"Number of Unique Values: {df[col].nunique()}")
        top_15 = df[col].value_counts().head(15)
        print("Top 15 Most Frequent Values:")
        for val, count in top_15.items():
            pct = (count / len(df)) * 100
            print(f"  - {val}: {count:,} ({pct:.1f}%)")


def analyze_specific_columns(df: pd.DataFrame):
    """Detailed check for requested target columns."""
    print_section("3. Specific Targeted Columns Analysis")
    target_mappings = [
        ("job_title", ["job_title"]),
        ("job_category", ["job_category"]),
        ("education_level", ["education_level", "education_required"]),
        ("location", ["location", "city", "country"]),
        ("work_mode", ["work_mode", "remote_work"]),
        ("company_size", ["company_size"]),
        ("industry", ["industry"]),
    ]

    for label, col_candidates in target_mappings:
        found_cols = [c for c in col_candidates if c in df.columns]
        if found_cols:
            for col in found_cols:
                print(f"\n[Target: {label}] Column found in dataset -> '{col}':")
                print(f"  - Unique Count: {df[col].nunique()}")
                top_5 = df[col].value_counts().head(5)
                top_str = ", ".join([f"{k} ({v})" for k, v in top_5.items()])
                print(f"  - Top 5: {top_str}")
        else:
            print(f"\n[Target: {label}] No exact matching column found in CSV.")


def analyze_skills(df: pd.DataFrame) -> pd.Series:
    """Analyzes the required_skills column by splitting delimiter and counting individual skills."""
    print_section("4. Skills Analysis")
    skills_col = "required_skills" if "required_skills" in df.columns else "skills"

    if skills_col not in df.columns:
        print(f"Skills column '{skills_col}' not found.")
        return pd.Series(dtype=int)

    # Detect delimiter
    sample_values = df[skills_col].dropna().head(10).tolist()
    delimiter = "|"
    for d in ["|", ",", ";"]:
        if any(d in str(val) for val in sample_values):
            delimiter = d
            break

    print(f"Detected skill separator: '{delimiter}'")

    # Split skills without altering df
    all_skills = (
        df[skills_col]
        .dropna()
        .astype(str)
        .str.split(delimiter)
        .explode()
        .str.strip()
    )
    all_skills = all_skills[all_skills != ""]
    skill_counts = all_skills.value_counts()

    print(f"Total Skill Mentions: {len(all_skills):,}")
    print(f"Unique Individual Skills: {len(skill_counts):,}")
    print("\nTop 30 Most Frequent Skills:")
    for rank, (skill, count) in enumerate(skill_counts.head(30).items(), 1):
        pct = (count / len(df)) * 100
        print(f"  {rank:2d}. {skill:<25} {count:4d} mentions ({pct:.1f}% of jobs)")

    return skill_counts


def analyze_numerical_statistics(df: pd.DataFrame):
    """Prints descriptive statistics for numerical metrics."""
    print_section("5. Numerical Columns Descriptive Statistics")
    target_num_cols = [
        "years_of_experience",
        "annual_salary_usd",
        "salary_min_usd",
        "salary_max_usd",
        "ai_salary_premium_pct",
        "demand_score",
        "demand_growth_yoy_pct",
        "benefits_score_10",
    ]

    existing_num_cols = [c for c in target_num_cols if c in df.columns]
    stats_df = df[existing_num_cols].describe().T
    stats_df = stats_df[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    print(stats_df.to_string())


def analyze_grouped_metrics(df: pd.DataFrame):
    """Prints grouped aggregations across job categories, experience, remote status, and LLM roles."""
    print_section("6. Grouped Analysis")

    if "job_category" in df.columns:
        print("\n--- Average Metrics by Job Category ---")
        cat_group = (
            df.groupby("job_category")
            .agg(
                avg_salary_usd=("annual_salary_usd", "mean"),
                avg_demand_score=("demand_score", "mean"),
                avg_demand_growth_yoy_pct=("demand_growth_yoy_pct", "mean"),
                job_count=("job_id", "count"),
            )
            .sort_values(by="avg_salary_usd", ascending=False)
        )
        print(cat_group.round(2).to_string())

    exp_col = "experience_level" if "experience_level" in df.columns else None
    if exp_col:
        print(f"\n--- Average Salary by Experience Level ('{exp_col}') ---")
        exp_group = (
            df.groupby(exp_col)["annual_salary_usd"]
            .agg(["count", "mean", "median", "std"])
            .sort_values(by="mean", ascending=False)
        )
        print(exp_group.round(2).to_string())

    remote_col = "is_remote_friendly" if "is_remote_friendly" in df.columns else ("remote_work" if "remote_work" in df.columns else None)
    if remote_col:
        print(f"\n--- Average Salary: Remote-Friendly vs Non-Remote ('{remote_col}') ---")
        remote_group = (
            df.groupby(remote_col)["annual_salary_usd"]
            .agg(["count", "mean", "median"])
        )
        print(remote_group.round(2).to_string())

    llm_col = "is_llm_role" if "is_llm_role" in df.columns else None
    if llm_col:
        print(f"\n--- Average Salary: LLM Roles vs Non-LLM Roles ('{llm_col}') ---")
        llm_group = (
            df.groupby(llm_col)["annual_salary_usd"]
            .agg(["count", "mean", "median"])
        )
        print(llm_group.round(2).to_string())


def generate_plots(df: pd.DataFrame, skill_counts: pd.Series, output_dir: Path):
    """Generates and saves required EDA visual plots into reports/eda/."""
    print_section("7. Generating EDA Visualizations")

    # 1. Salary Distribution
    plt.figure(figsize=(10, 5))
    sns.histplot(df["annual_salary_usd"], kde=True, bins=30, color="teal")
    plt.title("Annual Salary Distribution (USD)")
    plt.xlabel("Annual Salary (USD)")
    plt.ylabel("Frequency")
    salary_dist_path = output_dir / "salary_distribution.png"
    plt.savefig(salary_dist_path, dpi=300)
    plt.close()
    print(f" Saved: {salary_dist_path.name}")

    # 2. Demand Score Distribution
    plt.figure(figsize=(10, 5))
    sns.histplot(df["demand_score"], kde=True, bins=25, color="darkorange")
    plt.title("Demand Score Distribution")
    plt.xlabel("Demand Score (0 - 100)")
    plt.ylabel("Frequency")
    demand_dist_path = output_dir / "demand_score_distribution.png"
    plt.savefig(demand_dist_path, dpi=300)
    plt.close()
    print(f" Saved: {demand_dist_path.name}")

    # 3. Top 15 Job Categories
    plt.figure(figsize=(10, 6))
    top_cats = df["job_category"].value_counts().head(15)
    sns.barplot(x=top_cats.values, y=top_cats.index, palette="viridis")
    plt.title("Top 15 Job Categories")
    plt.xlabel("Job Count")
    plt.ylabel("Job Category")
    top_cat_path = output_dir / "top_15_job_categories.png"
    plt.savefig(top_cat_path, dpi=300)
    plt.close()
    print(f" Saved: {top_cat_path.name}")

    # 4. Top 20 Skills
    if not skill_counts.empty:
        plt.figure(figsize=(10, 7))
        top_20_skills = skill_counts.head(20)
        sns.barplot(x=top_20_skills.values, y=top_20_skills.index, palette="mako")
        plt.title("Top 20 Frequently Required Skills")
        plt.xlabel("Frequency Count")
        plt.ylabel("Skill")
        top_skills_path = output_dir / "top_20_skills.png"
        plt.savefig(top_skills_path, dpi=300)
        plt.close()
        print(f" Saved: {top_skills_path.name}")

    # 5. Average Salary by Job Category
    plt.figure(figsize=(10, 6))
    avg_sal_cat = (
        df.groupby("job_category")["annual_salary_usd"]
        .mean()
        .sort_values(ascending=False)
    )
    sns.barplot(x=avg_sal_cat.values, y=avg_sal_cat.index, palette="crest")
    plt.title("Average Annual Salary (USD) by Job Category")
    plt.xlabel("Average Annual Salary (USD)")
    plt.ylabel("Job Category")
    avg_sal_path = output_dir / "avg_salary_by_job_category.png"
    plt.savefig(avg_sal_path, dpi=300)
    plt.close()
    print(f" Saved: {avg_sal_path.name}")

    # 6. Demand Growth by Job Category
    plt.figure(figsize=(10, 6))
    avg_growth_cat = (
        df.groupby("job_category")["demand_growth_yoy_pct"]
        .mean()
        .sort_values(ascending=False)
    )
    sns.barplot(x=avg_growth_cat.values, y=avg_growth_cat.index, palette="magma")
    plt.title("Average YoY Demand Growth (%) by Job Category")
    plt.xlabel("Average YoY Demand Growth (%)")
    plt.ylabel("Job Category")
    growth_path = output_dir / "demand_growth_by_job_category.png"
    plt.savefig(growth_path, dpi=300)
    plt.close()
    print(f" Saved: {growth_path.name}")

    # 7. Salary vs Years of Experience
    plt.figure(figsize=(10, 6))
    sns.scatterplot(
        data=df,
        x="years_of_experience",
        y="annual_salary_usd",
        hue="job_category" if "job_category" in df.columns else None,
        alpha=0.7,
        s=60,
    )
    plt.title("Annual Salary vs. Years of Experience")
    plt.xlabel("Years of Experience")
    plt.ylabel("Annual Salary (USD)")
    if "job_category" in df.columns:
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    sal_vs_exp_path = output_dir / "salary_vs_years_of_experience.png"
    plt.savefig(sal_vs_exp_path, dpi=300)
    plt.close()
    print(f" Saved: {sal_vs_exp_path.name}")


def print_key_dataset_insights(df: pd.DataFrame, skill_counts: pd.Series):
    """Prints factual key dataset insights section without subjective recommendations."""
    total_records = len(df)
    num_job_cats = df["job_category"].nunique() if "job_category" in df.columns else 0
    top_3_cats = df["job_category"].value_counts().head(3)
    top_3_skills = skill_counts.head(3)

    sal_min = df["annual_salary_usd"].min()
    sal_max = df["annual_salary_usd"].max()
    sal_avg = df["annual_salary_usd"].mean()

    cat_demand = df.groupby("job_category")["demand_score"].mean().sort_values(ascending=False)
    highest_demand_cat = cat_demand.index[0]
    highest_demand_val = cat_demand.iloc[0]

    cat_growth = df.groupby("job_category")["demand_growth_yoy_pct"].mean().sort_values(ascending=False)
    highest_growth_cat = cat_growth.index[0]
    highest_growth_val = cat_growth.iloc[0]

    pct_remote = (df["is_remote_friendly"].mean() * 100) if "is_remote_friendly" in df.columns else 0.0
    pct_llm = (df["is_llm_role"].mean() * 100) if "is_llm_role" in df.columns else 0.0

    print("\n" + "=" * 80)
    print("================ KEY DATASET INSIGHTS ================")
    print("=" * 80)
    print(f"- Number of Records:              {total_records:,}")
    print(f"- Number of Job Categories:       {num_job_cats}")
    print(f"- Most Common Job Categories:     " + ", ".join([f"{cat} ({cnt})" for cat, cnt in top_3_cats.items()]))
    print(f"- Most Common Skills:             " + ", ".join([f"{sk} ({cnt})" for sk, cnt in top_3_skills.items()]))
    print(f"- Salary Range (USD):             ${sal_min:,.2f} - ${sal_max:,.2f}")
    print(f"- Average Salary (USD):           ${sal_avg:,.2f}")
    print(f"- Highest-Demand Category:        {highest_demand_cat} (Avg Demand Score: {highest_demand_val:.2f})")
    print(f"- Highest-Growth Category:        {highest_growth_cat} (Avg YoY Growth: {highest_growth_val:.2f}%)")
    print(f"- Percentage of Remote-Friendly Jobs: {pct_remote:.2f}%")
    print(f"- Percentage of LLM Roles:        {pct_llm:.2f}%")
    print("=" * 80 + "\n")


def main():
    setup_environment()
    data_file, output_dir = get_paths()

    if not data_file.exists():
        print(f"Error: Target dataset file not found at '{data_file}'")
        sys.exit(1)

    print(f"Loading dataset: {data_file.name}")
    df = pd.read_csv(data_file)

    analyze_overview(df)
    analyze_categorical_columns(df)
    analyze_specific_columns(df)
    skill_counts = analyze_skills(df)
    analyze_numerical_statistics(df)
    analyze_grouped_metrics(df)
    generate_plots(df, skill_counts, output_dir)
    print_key_dataset_insights(df, skill_counts)


if __name__ == "__main__":
    main()

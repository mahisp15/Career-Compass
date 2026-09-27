"""
CareerCompass - Dataset Inspection Script (Phase 3)

This script automatically discovers and inspects all CSV files inside data/raw/.
For each CSV, it reports:
  1. Dataset filename
  2. Number of rows
  3. Number of columns
  4. Complete list of column names
  5. Data type of every column
  6. Missing-value count for every column
  7. Missing-value percentage for every column
  8. Number of duplicate rows
  9. Number of unique values for every column
  10. First 5 rows
  11. Basic descriptive statistics for numerical columns

It concludes with a summary section across all discovered datasets.
"""

import sys
from pathlib import Path
import pandas as pd


def inspect_csv(file_path: Path) -> dict | None:
    """
    Inspects a single CSV file and prints a detailed report.

    Returns a dictionary of summary metrics for cross-dataset summary,
    or None if an error occurs while reading the CSV.
    """
    print("=" * 80)
    print(f"DATASET: {file_path.name}")
    print("=" * 80)

    try:
        df = pd.read_csv(file_path, low_memory=False)
    except Exception as e:
        print(f"ERROR: Failed to read {file_path.name}. Reason: {e}\n")
        return None

    num_rows = len(df)
    num_cols = len(df.columns)
    column_names = list(df.columns)
    duplicate_rows = int(df.duplicated().sum())
    total_missing = int(df.isnull().sum().sum())

    print(f"1. Filename:            {file_path.name}")
    print(f"2. Number of Rows:      {num_rows:,}")
    print(f"3. Number of Columns:   {num_cols}")
    print(f"4. Column Names:        {column_names}")

    print("\n5-7, 9. Column Details (Data Types, Missing Values, Unique Values):")
    missing_counts = df.isnull().sum()
    missing_pcts = (missing_counts / num_rows * 100) if num_rows > 0 else 0
    unique_counts = df.nunique()

    col_summary = pd.DataFrame({
        "Column Name": column_names,
        "Data Type": [str(dtype) for dtype in df.dtypes],
        "Missing Count": missing_counts.values,
        "Missing (%)": missing_pcts.round(2).values,
        "Unique Values": unique_counts.values,
    })
    print(col_summary.to_string(index=False))

    print(f"\n8. Number of Duplicate Rows: {duplicate_rows:,}")

    print("\n10. First 5 Rows:")
    print(df.head(5).to_string())

    print("\n11. Basic Descriptive Statistics (Numerical Columns):")
    numeric_df = df.select_dtypes(include=["number"])
    if not numeric_df.empty:
        print(numeric_df.describe().to_string())
    else:
        print("No numerical columns found in this dataset.")

    print("\n")

    return {
        "filename": file_path.name,
        "num_rows": num_rows,
        "num_cols": num_cols,
        "total_missing": total_missing,
        "duplicate_rows": duplicate_rows,
    }


def generate_summary_report(results: list[dict]) -> None:
    """Prints the overall summary report across all inspected datasets."""
    print("=" * 80)
    print("OVERALL DATASET SUMMARY REPORT")
    print("=" * 80)

    if not results:
        print("No datasets were successfully inspected.")
        return

    total_datasets = len(results)
    total_rows = sum(r["num_rows"] for r in results)

    dataset_most_rows = max(results, key=lambda x: x["num_rows"])
    dataset_most_missing = max(results, key=lambda x: x["total_missing"])
    dataset_most_duplicates = max(results, key=lambda x: x["duplicate_rows"])

    print(f"Total Number of Datasets:       {total_datasets}")
    print(f"Total Rows Across Datasets:     {total_rows:,}")
    print(
        f"Dataset with Most Rows:         {dataset_most_rows['filename']} ({dataset_most_rows['num_rows']:,} rows)"
    )
    print(
        f"Dataset with Most Missing Values: {dataset_most_missing['filename']} ({dataset_most_missing['total_missing']:,} missing values)"
    )
    print(
        f"Dataset with Most Duplicate Rows: {dataset_most_duplicates['filename']} ({dataset_most_duplicates['duplicate_rows']:,} duplicate rows)"
    )
    print("=" * 80)


def main():
    # Ensure stdout handles UTF-8 on Windows terminals
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Discover raw directory relative to script location or current working directory
    base_dir = Path(__file__).resolve().parent.parent
    raw_data_dir = base_dir / "data" / "raw"

    if not raw_data_dir.exists():
        print(f"Error: Directory '{raw_data_dir}' does not exist.")
        sys.exit(1)

    csv_files = sorted(list(raw_data_dir.glob("*.csv")))

    if not csv_files:
        print(f"No CSV files found in '{raw_data_dir}'.")
        sys.exit(0)

    print(f"Found {len(csv_files)} CSV file(s) in {raw_data_dir}\n")

    results = []
    for csv_file in csv_files:
        result = inspect_csv(csv_file)
        if result is not None:
            results.append(result)

    generate_summary_report(results)


if __name__ == "__main__":
    main()

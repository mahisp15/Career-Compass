import json
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent

JOBS_FILE = BASE_DIR / "data" / "processed" / "jobs_clean.csv"
LAYOFFS_FILE = BASE_DIR / "data" / "processed" / "layoffs_clean.csv"
COMPANY_REVIEWS_FILE = BASE_DIR / "data" / "processed" / "company_reviews_clean.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "company_market_trends.json"

# Load data
jobs_df = pd.read_csv(JOBS_FILE)
layoffs_df = pd.read_csv(LAYOFFS_FILE)
reviews_df = pd.read_csv(COMPANY_REVIEWS_FILE)

print(f"Jobs: {jobs_df.shape}")
print(f"Layoffs: {layoffs_df.shape}")
print(f"Reviews: {reviews_df.shape}")

# Get all unique companies from jobs
job_companies = jobs_df["employer_name"].dropna().unique()
layoff_companies = layoffs_df["Company"].dropna().unique()
review_companies = reviews_df["employer_name"].dropna().unique()

all_companies = set(job_companies) | set(layoff_companies) | set(review_companies)
print(f"Total unique companies across all datasets: {len(all_companies)}")

# Build market trend data for each company
company_trends = {}

for company in all_companies:
    trend_data = {
        "company": company,
        "has_job_postings": False,
        "has_layoffs": False,
        "has_reviews": False,
        "posting_volume_monthly": [],
        "posting_volume_total": 0,
        "recent_posting_trend": "unknown",
        "layoff_events": [],
        "layoff_summary": {
            "total_events": 0,
            "total_laid_off": 0,
            "recent_events_2026": 0,
            "departments_affected": []
        },
        "review_summary": {
            "avg_score": None,
            "sources": [],
            "total_reviews": 0
        }
    }
    
    # Job postings trend
    company_jobs = jobs_df[jobs_df["employer_name"] == company]
    if len(company_jobs) > 0:
        trend_data["has_job_postings"] = True
        trend_data["posting_volume_total"] = len(company_jobs)
        
        # Monthly posting volume
        if "posted_year" in company_jobs.columns and "posted_month" in company_jobs.columns:
            monthly = company_jobs.groupby(["posted_year", "posted_month"]).size().reset_index(name="count")
            monthly = monthly.sort_values(["posted_year", "posted_month"])
            
            for _, row in monthly.iterrows():
                trend_data["posting_volume_monthly"].append({
                    "year": int(row["posted_year"]),
                    "month": int(row["posted_month"]),
                    "postings": int(row["count"])
                })
            
            # Determine trend
            if len(monthly) >= 2:
                recent = monthly.tail(3)["count"].mean()
                older = monthly.head(max(1, len(monthly)-3))["count"].mean()
                if older > 0:
                    change = (recent - older) / older
                    if change > 0.3:
                        trend_data["recent_posting_trend"] = "growing"
                    elif change < -0.3:
                        trend_data["recent_posting_trend"] = "contracting"
                    else:
                        trend_data["recent_posting_trend"] = "stable"
    
    # Layoffs
    company_layoffs = layoffs_df[layoffs_df["Company"] == company]
    if len(company_layoffs) > 0:
        trend_data["has_layoffs"] = True
        trend_data["layoff_summary"]["total_events"] = len(company_layoffs)
        
        for _, row in company_layoffs.iterrows():
            laid_off = row.get("# Laid Off")
            date = row.get("Date")
            dept = row.get("department") if "department" in row else row.get("Department")
            pct = row.get("layoff_percentage")
            
            event = {
                "date": str(date) if pd.notna(date) else None,
                "laid_off": int(laid_off) if pd.notna(laid_off) else None,
                "percentage": float(pct) if pd.notna(pct) else None,
                "department": str(dept) if pd.notna(dept) else None,
                "source": str(row.get("Source")) if pd.notna(row.get("Source")) else None,
                "industry": str(row.get("Industry")) if pd.notna(row.get("Industry")) else None
            }
            trend_data["layoff_events"].append(event)
            
            if laid_off and pd.notna(laid_off):
                trend_data["layoff_summary"]["total_laid_off"] += int(laid_off)
            
            if date and str(date).startswith("2026"):
                trend_data["layoff_summary"]["recent_events_2026"] += 1
            
            if dept and pd.notna(dept):
                trend_data["layoff_summary"]["departments_affected"].append(str(dept))
    
    # Reviews
    company_reviews = reviews_df[reviews_df["employer_name"] == company]
    if len(company_reviews) > 0:
        trend_data["has_reviews"] = True
        scores = company_reviews["normalized_score"].dropna()
        if len(scores) > 0:
            trend_data["review_summary"]["avg_score"] = float(scores.mean())
            trend_data["review_summary"]["total_reviews"] = int(company_reviews["review_count"].sum())
            trend_data["review_summary"]["sources"] = company_reviews["publisher"].unique().tolist()
    
    company_trends[company] = trend_data

# Save
with open(OUTPUT_FILE, "w") as f:
    json.dump(company_trends, f, indent=2)

print(f"\nSaved company market trends to: {OUTPUT_FILE}")

# Print sample for well-known companies
test_companies = ["Google", "Microsoft", "Amazon", "Meta", "Tata Consultancy Services", "Barclays", "Cisco"]
for company in test_companies:
    if company in company_trends:
        data = company_trends[company]
        print(f"\n{company}:")
        print(f"  Job postings: {data['posting_volume_total']} (trend: {data['recent_posting_trend']})")
        print(f"  Has layoffs: {data['has_layoffs']} ({data['layoff_summary']['total_events']} events, {data['layoff_summary']['recent_events_2026']} in 2026)")
        print(f"  Has reviews: {data['has_reviews']} (avg: {data['review_summary']['avg_score']})")
        if data["layoff_events"]:
            for e in data["layoff_events"][:3]:
                print(f"    Layoff: {e['date']} - {e['laid_off']} people ({e['percentage']}%)")
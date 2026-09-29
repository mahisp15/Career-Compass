# Career Compass API Documentation

**Version:** 1.0.0  
**Base URL:** `http://127.0.0.1:8000`

## Overview

Career Compass API is a RESTful backend for an ML-based tech career advisory system. It provides endpoints for skill demand analysis, salary prediction, company recommendations, skill gap analysis, and market trend insights.

All data is derived from the Career Compass dataset consisting of:
- `ai_jobs_market_2025_2026.csv` - 1,500 AI job postings with structured skills
- `jobs.csv` - 675 additional job postings with company names
- `layoffs.csv` - 1,275 layoff records from layoffs.fyi
- `company_reviews.csv` - 157 company review records

---

## Authentication

No authentication required for current version.

---

## Endpoints

### 1. Health Check

**GET /** - Check API status

**Response:**
```json
{
  "project": "Career Compass",
  "status": "running"
}
```

---

### 2. Skills

#### GET /api/skills
Get all skills with demand metrics

**Response:** Array of skill objects
```json
[
  {
    "skill": "Python",
    "posting_count": 942,
    "avg_salary": 199822.72,
    "avg_demand_score": 89.71,
    "avg_demand_growth": 34.29,
    "demand_share_pct": 62.8,
    "demand_rank": 1
  }
]
```

#### GET /api/skills/{skill_name}
Get detailed information for a specific skill

**Path Parameters:**
- `skill_name` (string) - Skill name (case-insensitive)

**Response:**
```json
{
  "skill": "Python",
  "demand": {
    "skill": "Python",
    "posting_count": 942,
    "avg_salary": 199822.72,
    "avg_demand_score": 89.71,
    "avg_demand_growth": 34.29,
    "demand_share_pct": 62.8,
    "demand_rank": 1
  },
  "trend": {
    "skill": "Python",
    "trend": "Rising",
    "trend_slope": 0.112,
    "trend_p_value": 0.464,
    "trend_r_squared": 0.042,
    "first_month_demand_pct": 29.27,
    "last_month_demand_pct": 28.09,
    "percentage_change": -4.01,
    "total_postings": 942
  }
}
```

**Error:** 404 if skill not found

---

### 3. Trends

#### GET /api/trends
Get all skill trends

**Response:** Array of trend objects (see skill trend structure above)

#### GET /api/trends/{trend_type}
Get skills filtered by trend classification

**Path Parameters:**
- `trend_type` - One of: `Rising`, `Stable`, `Declining`

**Response:** Array of trend objects matching the type

**Error:** 400 if invalid trend type

---

### 4. Roles

#### GET /api/roles
Get all available roles with key skills

**Response:**
```json
[
  {
    "role": "AI Engineer",
    "category": "AI Engineering",
    "key_skills": ["Python", "Docker", "LLM Integration", "Cloud (AWS/GCP/Azure)", "PyTorch"],
    "total_postings": 391
  }
]
```

#### GET /api/categories
Get all job categories

**Response:** Array of category strings

---

### 5. Companies

#### GET /api/companies
Get all companies with basic profile info

**Response:**
```json
[
  {
    "name": "Tata Consultancy Services",
    "total_postings": 3,
    "countries": ["IN"],
    "top_skills": ["Cloud", "Python", "ML", "CI/CD", "Git"],
    "avg_review_score": 3.57,
    "has_layoffs": false
  }
]
```

#### GET /api/companies/{company_name}
Get detailed company profile and market trend

**Path Parameters:**
- `company_name` (string) - Company name (supports fuzzy matching)

**Response:**
```json
{
  "company": "Tata Consultancy Services",
  "market_trend": {
    "company": "Tata Consultancy Services",
    "has_job_postings": true,
    "has_layoffs": false,
    "has_reviews": true,
    "posting_volume_monthly": [
      {"year": 2026, "month": 5, "postings": 1},
      {"year": 2026, "month": 6, "postings": 2}
    ],
    "posting_volume_total": 3,
    "recent_posting_trend": "growing",
    "layoff_events": [],
    "layoff_summary": {
      "total_events": 0,
      "total_laid_off": 0,
      "recent_events_2026": 0,
      "departments_affected": []
    },
    "review_summary": {
      "avg_score": 3.57,
      "sources": ["AmbitionBox", "Glassdoor", "Indeed"],
      "total_reviews": 306014
    }
  },
  "profile": {
    "name": "Tata Consultancy Services",
    "total_postings": 3,
    "top_skills": [...],
    "top_roles": [...],
    "countries": ["IN"],
    "avg_review_score": 3.57,
    "has_layoffs": false
  }
}
```

**Error:** 404 if company not found

---

### 6. Model Metrics

#### GET /api/model/metrics
Get salary prediction model evaluation metrics and feature importance

**Response:**
```json
{
  "model_type": "XGBoost",
  "model_params": {
    "n_estimators": 300,
    "max_depth": 8,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42
  },
  "metrics": {
    "test_MAE": 91.02,
    "test_RMSE": 262.62,
    "test_R2": 0.9999,
    "cv_MAE": 122.03,
    "cv_MAE_std": 27.27
  },
  "alternative_model_metrics": {
    "LightGBM": {
      "MAE": 712.24,
      "RMSE": 1759.01,
      "R2": 0.9967
    }
  },
  "feature_importance_top_20": [
    {"feature": "demand_score", "importance": 0.1303},
    {"feature": "job_category_AI Engineering", "importance": 0.1181},
    ...
  ],
  "training_info": {
    "train_size": 1200,
    "test_size": 300,
    "target": "salary_midpoint",
    "note": "Features exclude all salary fields to prevent leakage..."
  }
}
```

---

### 7. Career Analysis (Main Endpoint)

#### POST /api/analyze
Comprehensive career analysis combining all ML components

**Request Body:**
```json
{
  "skills": ["Python", "SQL", "Git"],
  "target_role": "AI Engineering|AI Engineer",
  "target_company": "Tata Consultancy Services",
  "salary_expectation": 180000
}
```

**Fields:**
- `skills` (array of strings, **required**) - Current skill set
- `target_role` (string, optional) - Target role in format "Category|Role"
- `target_company` (string, optional) - Dream company name
- `salary_expectation` (number, optional) - Expected annual salary in USD

**Response:**
```json
{
  "career_summary": {
    "input_skills": ["Python", "SQL", "Git"],
    "target_role": "AI Engineering|AI Engineer",
    "target_company": "Tata Consultancy Services",
    "salary_expectation": 180000
  },
  "skill_gap_analysis": {
    "missing_skills_count": 12,
    "recommendations": [
      {
        "skill": "Cloud",
        "priority_score": 0.7076,
        "trend": "Rising",
        "trend_slope": 0.112,
        "posting_count": 402,
        "demand_share_pct": 26.8,
        "avg_demand_score": 87.47,
        "avg_demand_growth": 30.34,
        "avg_salary": 199788.56,
        "reasons": [
          "Rising trend (slope: 0.112)",
          "Appears in 402 postings",
          "Demand score: 87.5",
          "Required for target role (11 postings)"
        ],
        "role_relevant": true
      }
    ]
  },
  "salary_analysis": {
    "user_expectation": 180000,
    "predicted_salary": 151498,
    "salary_band": {
      "low": 136348,
      "high": 166648
    },
    "difference": 28502,
    "model_info": {
      "model_type": "XGBoost",
      "test_mae": 91.02,
      "cv_mae": 122.03
    }
  },
  "company_recommendations": [
    {
      "company": "Tata Consultancy Services",
      "similarity_score": 0.5606,
      "combined_score": 1.0426,
      "skill_match_pct": 56.1,
      "salary_compatibility": 1.0,
      "hiring_trend": "growing",
      "has_layoffs": false,
      "avg_review_score": 3.57,
      "avg_salary_midpoint": null,
      "top_skills": ["Cloud", "Python", "ML", "CI/CD", "Git"],
      "top_roles": ["Data Science & ML Engineering", "GEN AI Engineer"],
      "total_postings": 3,
      "explanations": [
        "Strong skill match (56.1% similarity)",
        "Hiring activity growing",
        "Company rating: 3.6/5"
      ]
    }
  ],
  "target_company_trend": {
    "company": "Tata Consultancy Services",
    "has_job_postings": true,
    "has_layoffs": false,
    "has_reviews": true,
    "posting_volume_monthly": [...],
    "posting_volume_total": 3,
    "recent_posting_trend": "growing",
    "layoff_events": [],
    "layoff_summary": {...},
    "review_summary": {...}
  },
  "role_recommendations": [
    {
      "role": "AI Business Analyst",
      "category": "Business",
      "match_score": 0.2684,
      "matching_skills": ["Python", "Git", "SQL"],
      "missing_skills": ["Cloud", "Linux", "Agile", "Research"]
    }
  ],
  "skill_trends_summary": {
    "rising": 3,
    "stable": 6,
    "declining": 3
  }
}
```

**Errors:**
- 400: Empty skills array
- 422: Invalid JSON

---

## Data Sources & Methodology

### Salary Prediction
- **Model:** XGBoost Regressor (300 estimators, max_depth=8, learning_rate=0.05)
- **Target:** `salary_midpoint` from job postings
- **Features:** Job title, category, experience level, location, company size, industry, skills (multi-hot encoded), demand metrics
- **Leakage Prevention:** All salary fields excluded from features
- **Metrics:** Test MAE = $91, CV MAE = $122 ± $27
- **Limitation:** Dataset has only 19 unique salary values; salary is nearly deterministic per job title

### Skill Trend Classification
- **Method:** Rolling linear regression on normalized monthly demand share (Jan 2025 - Mar 2026)
- **Thresholds:** Slope > 0.10 → Rising, < -0.10 → Declining, else Stable
- **Output:** 93 skills classified (16 Rising, 62 Stable, 15 Declining)
- **Interpretation:** Dataset-derived trend indicator, not industry-wide prediction

### Skill Gap Recommendations
- **Method:** Deterministic ranking using set difference + composite score
- **Score Components:**
  - Normalized posting frequency (30%)
  - Normalized demand share (20%)
  - Normalized demand score (20%)
  - Trend weight: Rising=1.5, Stable=1.0, Declining=0.5 (20%)
  - Role relevance (10%)
- **Output:** Prioritized missing skills with reasons

### Company Recommendations
- **Method:** Content-based cosine similarity between student skill vector and company hiring skill vectors
- **Filters:** Salary compatibility (±20%), hiring trend, layoff penalty, review score bonus
- **Explainability:** Each recommendation includes specific reasons

### Company Market Trend
- **Method:** Descriptive aggregation (not prediction)
- **Signals:** Posting volume trend, layoff events (correlational), review scores
- **Interpretation:** "Recent posting activity increased/decreased" - no future predictions

---

## Error Handling

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid input) |
| 404 | Not Found (skill/company not in dataset) |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

## Running the API

### Prerequisites
- Python 3.10+
- Virtual environment with dependencies

### Installation
```bash
cd Career-Compass-1
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Start Server
```bash
cd Career-Compass-1
venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000
```

### Run Tests
```bash
cd Career-Compass-1
venv\Scripts\python.exe -m pytest tests/test_api.py -v
```

---

## Example Usage

### Python
```python
import requests

# Get all skills
skills = requests.get("http://127.0.0.1:8000/api/skills").json()

# Analyze career
payload = {
    "skills": ["Python", "SQL", "Git"],
    "target_role": "AI Engineering|AI Engineer",
    "target_company": "Tata Consultancy Services",
    "salary_expectation": 180000
}
result = requests.post("http://127.0.0.1:8000/api/analyze", json=payload).json()
print(f"Predicted salary: ${result['salary_analysis']['predicted_salary']:,}")
print(f"Skill gaps: {result['skill_gap_analysis']['missing_skills_count']}")
```

### cURL
```bash
# Health check
curl http://127.0.0.1:8000/

# Get skills
curl http://127.0.0.1:8000/api/skills

# Analyze
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"skills": ["Python", "SQL"], "target_role": "AI Engineering|AI Engineer"}'
```

---

## Notes

- All recommendations are traceable to specific data points
- No external APIs or scraped data used
- Company salary data may be null if not available in job postings
- Layoff information is correlational context, not causal evidence
- Skill trends are dataset-specific observations over Jan 2025 - Mar 2026
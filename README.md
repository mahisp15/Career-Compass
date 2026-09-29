# Career Compass

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=111827)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)
![Career Guidance](https://img.shields.io/badge/Career-Guidance-brightgreen)
![Salary Prediction](https://img.shields.io/badge/Salary-Prediction-yellow)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-XGBoost%20%7C%20scikit--learn-orange)
![Status](https://img.shields.io/badge/Status-Active-success)

> **Career Compass** is an evidence-based career intelligence platform that helps engineering and technology students understand skill gaps, estimate salary expectations, compare companies, explore market trends, and discover suitable career roles.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Data and Machine Learning](#data-and-machine-learning)
- [Getting Started](#getting-started)
- [Running the Application](#running-the-application)
- [API Overview](#api-overview)
- [Example Request](#example-request)
- [Testing](#testing)
- [Limitations](#limitations)
- [Contributors](#contributors)
- [License](#license)

## Overview

Career decisions are often based on incomplete information, anecdotal advice, or outdated job-market assumptions. Career Compass addresses this problem by combining job postings, salary information, skill demand, company reviews, hiring activity, and layoff records into one interactive decision-support system.

A user provides:

- Current skills
- Target role
- Target company, if applicable
- Salary expectation

The platform returns:

- Prioritized skills to learn next
- Salary prediction and an estimated salary band
- Recommended companies
- Matching and alternative roles
- Target-company hiring and market signals
- Skill-demand trends
- Model performance information

The system is designed to provide **transparent recommendations**. Results include the data points and explanations behind the scores instead of returning unexplained rankings.

## Features

### Personalized career analysis

The `/api/analyze` endpoint combines the major components of the system into one response, which the frontend presents as a structured career readout.

### Skill-gap recommendations

Missing skills are ranked using a weighted score based on:

- Posting frequency: 30%
- Demand share: 20%
- Average demand score: 20%
- Market trend: 20%
- Relevance to the selected role: 10%

Rising skills receive a higher trend weight than stable or declining skills.

### Salary prediction

An XGBoost regression model estimates `salary_midpoint` using role, experience, location, company, industry, demand, and skill features. The frontend also displays a prediction range based on a ±10% presentation band.

### Company recommendations

Companies are ranked using content-based cosine similarity between the user's skill vector and company hiring-skill vectors. The ranking also considers:

- Salary compatibility
- Hiring trend
- Layoff signals
- Company review score
- Target-role relevance

Every recommendation contains supporting metrics and explanation text.

### Skill Explorer

Users can search and filter skills by:

- Rising
- Stable
- Declining
- All trends

The detail view displays posting volume, average salary, demand score, demand share, trend slope, and percentage change.

### Company market intelligence

Company profiles combine job postings, reviews, and layoffs to show:

- Total postings
- Monthly posting activity
- Hiring trend
- Layoff events
- Review score and review sources
- Top skills and roles
- Countries and remote-work information

## System Architecture

```text
                         ┌────────────────────────┐
                         │      React + Vite       │
                         │  Career Compass UI      │
                         └───────────┬────────────┘
                                     │ HTTP / JSON
                                     ▼
                         ┌────────────────────────┐
                         │      FastAPI API        │
                         │ backend/main.py         │
                         └───────┬────────┬────────┘
                                 │        │
                    ┌────────────┘        └─────────────┐
                    ▼                                   ▼
          ┌───────────────────┐              ┌───────────────────┐
          │ Precomputed data  │              │ Serialized ML     │
          │ CSV / JSON files  │              │ XGBoost model     │
          └─────────┬─────────┘              └───────────────────┘
                    ▲
                    │ offline pipeline
          ┌─────────┴─────────┐
          │ Raw job, review,  │
          │ and layoff data   │
          └───────────────────┘
```

The data-processing scripts run offline. They clean raw data, generate feature tables and JSON indexes, build recommendation vectors, and train the salary model. The API loads these artifacts at startup so request-time operations remain fast and deterministic.

## Technology Stack

### Backend and data science

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic
- Pandas
- NumPy
- scikit-learn
- XGBoost
- LightGBM for model comparison
- RapidFuzz for skill and company-name matching
- Joblib for model serialization
- Matplotlib and Seaborn for exploratory analysis

### Frontend

- React 19
- Vite
- JavaScript
- CSS custom properties and responsive CSS
- ESLint

## Repository Structure

```text
Career-Compass/
├── backend/
│   └── main.py                         # FastAPI application and decision engine
├── data/
│   ├── raw/                            # Source CSV datasets
│   └── processed/                      # Cleaned and derived CSV/JSON artifacts
├── docs/
│   ├── API_DOCUMENTATION.md            # Detailed API reference
│   ├── 01_data_engineering_and_eda.md
│   ├── 02_market_intelligence_and_recommendation_features.md
│   ├── 03_salary_prediction_and_ml_model.md
│   ├── 04_fastapi_backend_and_decision_engine.md
│   └── 05_react_frontend_integration_and_testing.md
├── frontend/
│   ├── src/
│   │   ├── App.jsx                     # Main React application
│   │   ├── App.css                     # UI design system and responsive styles
│   │   ├── index.css                   # Global styles
│   │   └── services/api.js              # Centralized API client
│   ├── .env.example                    # Frontend API configuration
│   ├── package.json
│   └── vite.config.js
├── models/
│   ├── salary_model.pkl                # Trained XGBoost model
│   ├── salary_preprocessor.pkl         # Fitted preprocessing pipeline
│   └── salary_model_metadata.json      # Schema, metrics, and model metadata
├── reports/
│   └── eda/                            # Generated exploratory-analysis plots
├── scripts/
│   ├── clean_*.py                      # Dataset cleaning pipelines
│   ├── build_*.py                      # Feature and recommendation builders
│   ├── analyze_*.py                    # EDA and trend analysis
│   └── train_salary_model.py           # Model training and evaluation
├── tests/
│   └── test_api.py                     # Backend API tests
├── requirements.txt
└── README.md
```

## Data and Machine Learning

### Source datasets

The current project snapshot includes:

| Dataset | Records | Purpose |
|---|---:|---|
| `ai_jobs_market_2025_2026.csv` | 1,500 | AI job attributes, salaries, skills, demand, and growth |
| `jobs.csv` | 675 | Company job postings and hiring information |
| `layoffs.csv` | 1,275 | Company layoff events and affected departments |
| `company_reviews.csv` | 159 | Company ratings and review metadata |

The cleaned outputs are stored in `data/processed/` and are consumed by the API.

### Derived artifacts

The offline feature pipeline produces:

- `skill_demand.csv` — skill frequency, demand, salary, and ranking metrics.
- `skill_trends.csv` — monthly skill-demand trend classifications.
- `skill_taxonomy.json` — canonical skills, categories, roles, countries, and industries.
- `role_skill_mapping.json` — role-specific and category-specific skill frequencies.
- `company_profiles.json` — aggregated company hiring profiles.
- `company_market_trends.json` — job, layoff, and review signals for companies.
- `company_recommendations_engine.json` — normalized company skill vectors and metadata.

### Salary model

The primary model is an XGBoost regressor with:

```text
n_estimators     = 300
max_depth        = 8
learning_rate    = 0.05
subsample        = 0.8
colsample_bytree = 0.8
random_state     = 42
```

The target is `salary_midpoint`. Direct salary fields are excluded from the input features to reduce target leakage. Categorical fields are one-hot encoded, numerical fields are standardized, and frequently occurring skills are multi-hot encoded.

The checked-in metadata reports:

| Metric | Value |
|---|---:|
| Test MAE | 91.02 |
| Test RMSE | 262.62 |
| Test R² | 0.999926 |
| Five-fold CV MAE | 122.03 |
| CV MAE standard deviation | 27.27 |

These metrics are specific to the current dataset. The salary target has only 19 unique values and is nearly deterministic by job title, so the unusually strong scores should not be interpreted as real-world salary accuracy.

### Skill trend methodology

Skill trends are computed from monthly demand share. A linear regression slope classifies each skill as:

```text
slope >  0.10  → Rising
slope < -0.10  → Declining
otherwise      → Stable
```

This is a descriptive, dataset-derived signal and not a forecast of the complete technology industry.

## Getting Started

### Prerequisites

Install the following before running the project:

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- Git

### Clone the repository

```bash
git clone https://github.com/mahisp15/Career-Compass.git
cd Career-Compass
```

### Set up the backend

Create and activate a virtual environment:

#### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

The test suite additionally requires `pytest`. Depending on the installed FastAPI/Starlette version, the Starlette test client may also require `httpx2`:

```bash
pip install pytest httpx2
```

### Set up the frontend

```bash
cd frontend
npm ci
```

The frontend uses the API URL from `frontend/.env`. To create it from the example:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

The default value is:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Running the Application

Run the backend and frontend in separate terminals.

### Terminal 1 — FastAPI backend

From the repository root, with the virtual environment active:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The API will be available at:

- Application: <http://127.0.0.1:8000>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

### Terminal 2 — React frontend

```bash
cd frontend
npm run dev
```

Open the Vite development URL shown in the terminal, normally:

<http://localhost:5173>

### Production frontend build

```bash
cd frontend
npm run build
npm run preview
```

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API health check |
| `GET` | `/api/skills` | Return skill demand records |
| `GET` | `/api/skills/{skill_name}` | Return one skill’s demand and trend |
| `GET` | `/api/trends` | Return all skill trends |
| `GET` | `/api/trends/{trend_type}` | Filter trends by Rising, Stable, or Declining |
| `GET` | `/api/roles` | Return available roles and key skills |
| `GET` | `/api/categories` | Return job categories |
| `GET` | `/api/companies` | Return company profile summaries |
| `GET` | `/api/companies/{company_name}` | Return a company profile and market trend |
| `GET` | `/api/model/metrics` | Return salary-model metrics and feature importance |
| `POST` | `/api/analyze` | Return a complete career analysis |

For the complete request and response schemas, see [`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md).

## Example Request

### cURL

```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "skills": ["Python", "SQL", "Git"],
    "target_role": "AI Engineering|AI Engineer",
    "target_company": "Tata Consultancy Services",
    "salary_expectation": 180000
  }'
```

### Python

```python
import requests

payload = {
    "skills": ["Python", "SQL", "Git"],
    "target_role": "AI Engineering|AI Engineer",
    "target_company": "Tata Consultancy Services",
    "salary_expectation": 180000,
}

response = requests.post(
    "http://127.0.0.1:8000/api/analyze",
    json=payload,
)
response.raise_for_status()
result = response.json()

print("Predicted salary:", result["salary_analysis"]["predicted_salary"])
print("Top skill gap:", result["skill_gap_analysis"]["recommendations"][0]["skill"])
```

## Testing

### Backend tests

From the repository root, with the virtual environment active:

```bash
pytest tests/test_api.py -v
```

The test suite covers health checks, skills, trends, roles, categories, companies, model metrics, validation errors, salary analysis, skill-gap recommendations, and company recommendations.

### Frontend checks

```bash
cd frontend
npm run lint
npm run build
```

## Rebuilding Data and Model Artifacts

The repository includes generated processed data and model files, so rebuilding is optional for normal use. If the raw data changes, run the pipelines in dependency order from the repository root:

```bash
python scripts/clean_ai_jobs_market.py
python scripts/clean_jobs.py
python scripts/clean_layoffs.py
python scripts/clean_company_reviews.py

python scripts/build_skill_dataset.py
python scripts/build_skill_trends.py
python scripts/build_role_skill_mapping.py
python scripts/build_company_profiles.py
python scripts/build_company_market_trends.py
python scripts/build_company_recommendations.py

python scripts/train_salary_model.py
```

For exploratory analysis:

```bash
python scripts/inspect_datasets.py
python scripts/analyze_ai_jobs_market.py
```

Generated EDA charts are written to `reports/eda/`.

## Limitations

- This is a research and academic prototype, not a production recruitment or compensation platform.
- The datasets are finite snapshots rather than live market feeds.
- Company-name matching can be affected by spelling and alias differences across datasets.
- Skill extraction uses canonical matching and fuzzy matching, so synonyms may not always be recognized.
- Company salary information may be unavailable for some companies.
- Layoff data is contextual and correlational; it is not evidence of future company performance.
- Recommendation scores are deterministic heuristics, not calibrated probabilities.
- The salary model’s very strong metrics are influenced by the limited number of unique salary levels in the dataset.
- The current API has no authentication, persistence, rate limiting, or user accounts.

## Contributors

Career Compass was developed collaboratively by a team of five. The project contributions are organized into the following technical areas:

1. Data engineering, cleaning, validation, and exploratory analysis.
2. Market intelligence, skill trends, role mappings, and company feature engineering.
3. Salary prediction and machine-learning model development.
4. FastAPI backend and explainable recommendation engine.
5. React frontend, API integration, user experience, and testing.

Detailed contribution guides are available in the [`docs/`](docs/) directory.

## License

No license has been specified for this repository yet. Add a `LICENSE` file before distributing or reusing the project publicly under a particular license.

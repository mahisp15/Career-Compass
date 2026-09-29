import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "Career Compass"
    assert data["status"] == "running"


def test_get_skills():
    response = client.get("/api/skills")
    assert response.status_code == 200
    skills = response.json()
    assert isinstance(skills, list)
    assert len(skills) > 0
    # Check structure
    for skill in skills:
        assert "skill" in skill
        assert "posting_count" in skill
        assert "demand_rank" in skill


def test_get_skill_by_name():
    response = client.get("/api/skills/Python")
    assert response.status_code == 200
    data = response.json()
    assert data["skill"] == "Python"
    assert "demand" in data
    assert "trend" in data


def test_get_skill_not_found():
    response = client.get("/api/skills/NonExistentSkill123")
    assert response.status_code == 404


def test_get_trends():
    response = client.get("/api/trends")
    assert response.status_code == 200
    trends = response.json()
    assert isinstance(trends, list)
    assert len(trends) > 0


def test_get_trends_by_type():
    for trend_type in ["Rising", "Stable", "Declining"]:
        response = client.get(f"/api/trends/{trend_type}")
        assert response.status_code == 200
        trends = response.json()
        assert all(t["trend"] == trend_type for t in trends)


def test_get_trends_invalid_type():
    response = client.get("/api/trends/InvalidType")
    assert response.status_code == 400


def test_get_roles():
    response = client.get("/api/roles")
    assert response.status_code == 200
    roles = response.json()
    assert isinstance(roles, list)
    assert len(roles) > 0
    for role in roles:
        assert "role" in role
        assert "category" in role
        assert "key_skills" in role
        assert "total_postings" in role


def test_get_categories():
    response = client.get("/api/categories")
    assert response.status_code == 200
    categories = response.json()
    assert isinstance(categories, list)
    assert len(categories) > 0


def test_get_companies():
    response = client.get("/api/companies")
    assert response.status_code == 200
    companies = response.json()
    assert isinstance(companies, list)
    assert len(companies) > 0
    for company in companies:
        assert "name" in company
        assert "total_postings" in company
        assert "countries" in company


def test_get_company():
    response = client.get("/api/companies/Tata Consultancy Services")
    assert response.status_code == 200
    data = response.json()
    assert data["company"] == "Tata Consultancy Services"
    assert "market_trend" in data
    assert "profile" in data


def test_get_company_not_found():
    response = client.get("/api/companies/NonExistentCompany123")
    assert response.status_code == 404


def test_get_model_metrics():
    response = client.get("/api/model/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "model_type" in data
    assert data["model_type"] == "XGBoost"
    assert "metrics" in data
    assert "test_MAE" in data["metrics"]
    assert "test_RMSE" in data["metrics"]
    assert "test_R2" in data["metrics"]


def test_analyze_endpoint():
    payload = {
        "skills": ["Python", "SQL", "Git"],
        "target_role": "AI Engineering|AI Engineer",
        "target_company": "Tata Consultancy Services",
        "salary_expectation": 180000
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Check career_summary
    assert "career_summary" in data
    assert data["career_summary"]["input_skills"] == ["Python", "SQL", "Git"]
    assert data["career_summary"]["target_role"] == "AI Engineering|AI Engineer"
    assert data["career_summary"]["target_company"] == "Tata Consultancy Services"
    assert data["career_summary"]["salary_expectation"] == 180000

    # Check skill_gap_analysis
    assert "skill_gap_analysis" in data
    assert "missing_skills_count" in data["skill_gap_analysis"]
    assert "recommendations" in data["skill_gap_analysis"]
    assert isinstance(data["skill_gap_analysis"]["recommendations"], list)
    assert len(data["skill_gap_analysis"]["recommendations"]) > 0

    # Check salary_analysis
    assert "salary_analysis" in data
    assert "user_expectation" in data["salary_analysis"]
    assert "predicted_salary" in data["salary_analysis"]
    assert "salary_band" in data["salary_analysis"]
    assert "low" in data["salary_analysis"]["salary_band"]
    assert "high" in data["salary_analysis"]["salary_band"]
    assert "model_info" in data["salary_analysis"]

    # Check company_recommendations
    assert "company_recommendations" in data
    assert isinstance(data["company_recommendations"], list)
    assert len(data["company_recommendations"]) > 0
    for comp in data["company_recommendations"]:
        assert "company" in comp
        assert "similarity_score" in comp
        assert "combined_score" in comp
        assert "skill_match_pct" in comp
        assert "explanations" in comp

    # Check target_company_trend
    assert "target_company_trend" in data
    assert data["target_company_trend"] is not None
    assert data["target_company_trend"]["company"] == "Tata Consultancy Services"

    # Check role_recommendations
    assert "role_recommendations" in data
    assert isinstance(data["role_recommendations"], list)


def test_analyze_empty_skills():
    payload = {
        "skills": [],
        "target_role": "AI Engineering|AI Engineer",
        "target_company": "Tata Consultancy Services",
        "salary_expectation": 180000
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 400


def test_analyze_missing_required_fields():
    payload = {
        "skills": ["Python", "SQL"]
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200  # Optional fields can be missing


def test_analyze_unknown_company():
    payload = {
        "skills": ["Python", "SQL"],
        "target_company": "NonExistentCompany123"
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Target company trend should be null for unknown company
    assert data["target_company_trend"] is None


def test_analyze_unknown_skill():
    payload = {
        "skills": ["Python", "NonExistentSkillXYZ123"],
        "target_role": "AI Engineering|AI Engineer"
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200


def test_skill_gap_recommendations_structure():
    payload = {
        "skills": ["Python", "SQL"],
        "target_role": "AI Engineering|AI Engineer"
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    recommendations = data["skill_gap_analysis"]["recommendations"]
    for rec in recommendations:
        assert "skill" in rec
        assert "priority_score" in rec
        assert "trend" in rec
        assert "trend_slope" in rec
        assert "posting_count" in rec
        assert "demand_share_pct" in rec
        assert "avg_demand_score" in rec
        assert "reasons" in rec
        assert isinstance(rec["reasons"], list)
        assert len(rec["reasons"]) > 0
        assert rec["trend"] in ["Rising", "Stable", "Declining"]


def test_company_recommendations_structure():
    payload = {
        "skills": ["Python", "SQL", "Git"],
        "target_role": "AI Engineering|AI Engineer",
        "salary_expectation": 150000
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    for comp in data["company_recommendations"]:
        assert "company" in comp
        assert "similarity_score" in comp
        assert "combined_score" in comp
        assert "skill_match_pct" in comp
        assert "salary_compatibility" in comp
        assert "hiring_trend" in comp
        assert "has_layoffs" in comp
        assert "top_skills" in comp
        assert "top_roles" in comp
        assert "total_postings" in comp
        assert "explanations" in comp
        assert isinstance(comp["explanations"], list)


def test_salary_prediction_reasonable():
    payload = {
        "skills": ["Python", "SQL", "Git"],
        "target_role": "AI Engineering|AI Engineer",
        "salary_expectation": 180000
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    pred = data["salary_analysis"]["predicted_salary"]
    # Salary should be in reasonable range
    assert 100000 <= pred <= 400000
    band = data["salary_analysis"]["salary_band"]
    assert band["low"] < pred < band["high"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
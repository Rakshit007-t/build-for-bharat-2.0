from fastapi.testclient import TestClient

from backend.main import app
from backend.services.analysis_service import AnalysisService
from backend.services.model_service import ModelService
from backend.services.talent_service import TalentProfileService
from backend.schemas.api_models import TalentProfileInput


def test_talent_profile_uses_aggregate_skill_vocabulary_only():
    summary = {
        "skill_vocabulary": [
            {"name": "python", "count": 50}, {"name": "sql", "count": 45},
            {"name": "machine learning", "count": 30}, {"name": "analytics", "count": 40},
        ],
        "top_skills": [
            {"name": "analytics", "count": 40}, {"name": "sql", "count": 45},
            {"name": "python", "count": 50},
        ],
        "top_roles": [{"name": "Data Scientist", "count": 15}, {"name": "Data Analyst", "count": 20}],
    }
    result = TalentProfileService().analyze(TalentProfileInput(skills=["python", "sql", "machine_learning"]), summary)
    assert result.analysis_type == "descriptive_overlap"
    assert result.overlap_percent == 100
    assert [row.label for row in result.matched_skills] == ["Python", "SQL", "Machine Learning"]
    assert result.top_role_categories[0].role == "Data Scientist"
    assert "not a hiring probability" in result.explanation
    assert "no row-level join key" in result.role_matching_note
    assert "Analytics Jobs" in result.skill_frequency_note


def test_talent_profile_endpoint_returns_aggregates_not_rows():
    app.state.analysis_service = AnalysisService()
    app.state.model_service = ModelService()
    with TestClient(app) as client:
        response = client.post("/api/talent/profile", json={"skills": ["python", "sql", "machine_learning"]})
        empty = client.post("/api/talent/profile", json={"skills": []})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Descriptive job-market alignment"
    assert len(body["top_role_categories"]) <= 5
    assert "raw" not in str(body).lower()
    assert empty.status_code == 422
    assert empty.json()["status"] == "validation_error"

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.analysis_service import AnalysisService
from backend.services.model_service import ModelService


def make_client(tmp_path):
    app.state.analysis_service = AnalysisService(tmp_path)
    app.state.model_service = ModelService(tmp_path)
    return TestClient(app)


def test_health_works(tmp_path):
    with make_client(tmp_path) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/health").json() == {"status": "ok"}


def test_readiness_works_with_missing_artifacts(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["analysis"]["status"] == "artifact_missing"
    assert body["models"]["jds"]["status"] == "artifact_missing"
    assert body["models"]["sds"]["status"] == "artifact_missing"


def test_models_endpoint_handles_missing_artifacts(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/models")
    assert response.status_code == 200
    assert response.json()["jds"]["status"] == "artifact_missing"
    assert response.json()["sds"]["status"] == "artifact_missing"


def test_jds_prediction_is_not_ready_without_artifact(tmp_path):
    payload = {
        "big_data_skills": 1,
        "maths_stats_skills": 1,
        "coding_skills": 1,
        "ai_and_ml_skills": 1,
        "dashboard_and_storytelling_skills": 1,
    }
    with make_client(tmp_path) as client:
        response = client.post("/api/models/jds/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "artifact_missing"
    assert response.json()["prediction"] is None


def test_sds_prediction_is_not_ready_without_artifact(tmp_path):
    payload = {
        "neuroticism": 1,
        "extraversion": 1,
        "openness_to_experience": 1,
        "agreeableness": 1,
        "conscientiousness": 1,
    }
    with make_client(tmp_path) as client:
        response = client.post("/api/models/sds/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "artifact_missing"
    assert response.json()["prediction"] is None


def test_malformed_prediction_input_returns_422(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post("/api/models/jds/predict", json={"big_data_skills": "not-a-number"})
    assert response.status_code == 422


def test_missing_analysis_artifact_is_not_ready(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/analysis/job-market")
    assert response.status_code == 200
    assert response.json()["status"] == "artifact_missing"
    assert response.json()["summary"] is None


def test_static_frontend_still_serves(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "Ghost Skills" in response.text

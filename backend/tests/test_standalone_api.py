import json

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.analysis_service import AnalysisService
from backend.services.model_service import ModelService


def setup_client(tmp_path):
    app.state.analysis_service = AnalysisService(tmp_path / "artifacts")
    app.state.model_service = ModelService(tmp_path / "artifacts")
    client = TestClient(app)
    return client


def test_summary_endpoint_is_dashboard_safe_and_not_fabricated(tmp_path):
    with setup_client(tmp_path) as client:
        response = client.get("/api/reports/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"not_ready", "partial", "ready"}
    assert "dataset_row_counts" in body
    assert "models" in body
    assert "training_rows" not in json.dumps(body)


def test_figures_endpoint_handles_empty_artifact_directory(tmp_path):
    with setup_client(tmp_path) as client:
        response = client.get("/api/figures")
    assert response.status_code == 200
    assert all(item["path"].startswith("/api/figures/") for item in response.json()["figures"])


def test_corrupt_artifacts_return_invalid_state(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "jds_model.pkl").write_bytes(b"not a pickle")
    (artifacts / "jds_metadata.json").write_text("{bad json", encoding="utf-8")
    with setup_client(tmp_path) as client:
        response = client.get("/api/models")
    assert response.status_code == 200
    assert response.json()["jds"]["status"] == "artifact_invalid"


def test_figure_path_traversal_is_rejected(tmp_path):
    with setup_client(tmp_path) as client:
        response = client.get("/api/figures/../../README.md")
    assert response.status_code == 404


def test_malformed_prediction_has_structured_validation_error(tmp_path):
    with setup_client(tmp_path) as client:
        response = client.post("/api/models/jds/predict", json={"big_data_skills": "nan"})
    assert response.status_code == 422
    assert response.json()["status"] == "validation_error"


def test_health_route_remains_available(tmp_path):
    with setup_client(tmp_path) as client:
        assert client.get("/health").json() == {"status": "ok"}

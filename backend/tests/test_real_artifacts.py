import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.analysis_service import AnalysisService
from backend.services.model_service import ModelService


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "model" / "artifacts"


@pytest.mark.parametrize("key", ["jds", "sds"])
def test_generated_model_artifact_predicts_only_declared_class(key):
    metadata_path = ARTIFACTS / f"{key}_metadata.json"
    model_path = ARTIFACTS / f"{key}_model.pkl"
    if not metadata_path.is_file() or not model_path.is_file():
        pytest.skip("Run model/src/run_pipeline.py to generate local artifacts.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload = {name: (limits["min"] + limits["max"]) / 2 for name, limits in metadata["feature_ranges"].items()}
    app.state.analysis_service = AnalysisService()
    app.state.model_service = ModelService()
    with TestClient(app) as client:
        response = client.post(f"/api/models/{key}/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["prediction"] in metadata["class_labels"]
    assert "training_rows" not in body["model"]


def test_out_of_range_prediction_is_a_validation_error():
    metadata_path = ARTIFACTS / "jds_metadata.json"
    if not metadata_path.is_file():
        pytest.skip("Run model/src/run_pipeline.py to generate local artifacts.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload = {name: (limits["min"] + limits["max"]) / 2 for name, limits in metadata["feature_ranges"].items()}
    payload["big_data_skills"] = metadata["feature_ranges"]["big_data_skills"]["max"] + 1
    app.state.analysis_service = AnalysisService()
    app.state.model_service = ModelService()
    with TestClient(app) as client:
        response = client.post("/api/models/jds/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "validation_error"
    assert response.json()["prediction"] is None


def test_generated_market_summary_is_validated_and_aggregated():
    path = ARTIFACTS / "job_market_summary.json"
    if not path.is_file():
        pytest.skip("Run model/src/run_pipeline.py to generate local artifacts.")
    app.state.analysis_service = AnalysisService()
    app.state.model_service = ModelService()
    with TestClient(app) as client:
        analysis = client.get("/api/analysis/job-market")
        report = client.get("/api/reports/summary")
        figures = client.get("/api/figures")
    assert analysis.status_code == report.status_code == figures.status_code == 200
    assert analysis.json()["status"] == "ready"
    assert report.json()["status"] == "ready"
    assert report.json()["dataset_row_counts"]["jds"] == 139
    assert figures.json()["figures"]

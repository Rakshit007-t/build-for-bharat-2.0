from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.schemas.api_models import (
    HealthResponse,
    JdsPredictionInput,
    JobMarketResponse,
    ModelsResponse,
    PredictionResponse,
    ReadinessResponse,
    SdsPredictionInput,
)
from backend.services.analysis_service import AnalysisService
from backend.services.model_service import ModelService

app = FastAPI(title="Ghost Skills API", version="0.1.0")
app.state.analysis_service = AnalysisService()
app.state.model_service = ModelService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> HealthResponse:
    return {"status": "ok"}


@app.get("/api/health", response_model=HealthResponse)
def api_health_check() -> HealthResponse:
    return {"status": "ok"}


@app.get("/api/readiness", response_model=ReadinessResponse)
def readiness() -> ReadinessResponse:
    analysis = app.state.analysis_service.get_job_market_summary()
    models = app.state.model_service.get_readiness()
    model_components = {key: value for key, value in models.items()}
    all_ready = analysis.status == "ready" and all(item["status"] == "ready" for item in model_components.values())
    return ReadinessResponse(
        status="ready" if all_ready else "not_ready",
        analysis={"status": analysis.status, "detail": analysis.detail},
        models=model_components,
    )


@app.get("/api/analysis/job-market", response_model=JobMarketResponse)
def job_market_summary() -> JobMarketResponse:
    return app.state.analysis_service.get_job_market_summary()


@app.get("/api/models", response_model=ModelsResponse)
def models() -> ModelsResponse:
    return app.state.model_service.get_models()


@app.post("/api/models/jds/predict", response_model=PredictionResponse)
def predict_jds(payload: JdsPredictionInput) -> PredictionResponse:
    return app.state.model_service.predict("jds", payload.model_dump())


@app.post("/api/models/sds/predict", response_model=PredictionResponse)
def predict_sds(payload: SdsPredictionInput) -> PredictionResponse:
    return app.state.model_service.predict("sds", payload.model_dump())


# Serve static frontend files at root (mounted AFTER API routes so API endpoints take precedence)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

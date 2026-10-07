from pathlib import Path
import json
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.schemas.api_models import (
    HealthResponse,
    DashboardSummaryResponse,
    FiguresResponse,
    JdsPredictionInput,
    JobMarketResponse,
    ModelsResponse,
    PredictionResponse,
    ReadinessResponse,
    SdsPredictionInput,
    TalentProfileInput,
    TalentProfileResponse,
)
from backend.services.analysis_service import AnalysisService
from backend.services.model_service import ModelService
from backend.services.talent_service import TalentProfileService

app = FastAPI(title="Ghost Skills API", version="0.1.0")
app.state.analysis_service = AnalysisService()
app.state.model_service = ModelService()
app.state.talent_profile_service = TalentProfileService()


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(part) for part in error["loc"] if part != "body"), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"status": "validation_error", "detail": details})

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


@app.post("/api/talent/profile", response_model=TalentProfileResponse)
def talent_profile(payload: TalentProfileInput) -> TalentProfileResponse:
    market = app.state.analysis_service.get_job_market_summary()
    if market.status != "ready" or market.summary is None:
        raise HTTPException(status_code=503, detail=market.detail or "Local job-market summary is unavailable.")
    return app.state.talent_profile_service.analyze(payload, market.summary.model_dump())


@app.get("/api/models", response_model=ModelsResponse)
def models() -> ModelsResponse:
    return app.state.model_service.get_models()


@app.get("/api/reports/summary", response_model=DashboardSummaryResponse)
def dashboard_summary() -> DashboardSummaryResponse:
    root = Path(__file__).resolve().parent.parent
    quality_path = root / "data" / "reports" / "data_quality_report.json"
    quality = {}
    if quality_path.is_file():
        try:
            quality = json.loads(quality_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            quality = {}

    analysis_response = app.state.analysis_service.get_job_market_summary()
    models_response = app.state.model_service.get_models()
    row_counts = {
        name: int(entry["audit"]["rows"])
        for name, entry in quality.get("datasets", {}).items()
        if isinstance(entry, dict) and isinstance(entry.get("audit"), dict) and isinstance(entry["audit"].get("rows"), int)
    }
    model_data = {}
    limitations = []
    for name in ("jds", "sds"):
        info = getattr(models_response, name)
        metadata = info.metadata
        model_data[name] = {
            "status": info.status,
            "target": info.target,
            "model_name": metadata.model_name if metadata else None,
            "model_version": metadata.model_version if metadata else None,
            "algorithm": metadata.algorithm if metadata else None,
            "validation_metrics": metadata.validation_metrics if metadata else {},
        }
        if metadata:
            limitations.extend(metadata.limitations)
    if analysis_response.summary:
        limitations.extend(analysis_response.summary.limitations)
    ready = quality.get("status") == "complete" and analysis_response.status == "ready" and all(item["status"] == "ready" for item in model_data.values())
    partial = bool(row_counts or analysis_response.status == "ready" or any(item["status"] == "ready" for item in model_data.values()))
    timestamps = []
    if analysis_response.summary:
        timestamps.append(analysis_response.summary.generated_at)
    for name in ("jds", "sds"):
        metadata = getattr(models_response, name).metadata
        if metadata and metadata.created_at:
            timestamps.append(metadata.created_at)
    quality_time = quality.get("generated_at")
    if quality_time:
        try:
            timestamps.append(datetime.fromisoformat(str(quality_time).replace("Z", "+00:00")))
        except ValueError:
            pass
    return DashboardSummaryResponse(
        status="ready" if ready else "partial" if partial else "not_ready",
        dataset_row_counts=row_counts,
        job_market=analysis_response.summary,
        models=model_data,
        important_limitations=list(dict.fromkeys(limitations)),
        generated_at=max(timestamps) if timestamps else None,
    )


@app.get("/api/figures", response_model=FiguresResponse)
def available_figures() -> FiguresResponse:
    figures_root = Path(__file__).resolve().parent.parent / "model" / "figures"
    figures = []
    if figures_root.is_dir():
        for figure in sorted(figures_root.rglob("*.png")):
            relative = figure.relative_to(figures_root).as_posix()
            figures.append({"name": figure.stem.replace("_", " ").title(), "path": f"/api/figures/{quote(relative, safe='/')}"})
    return FiguresResponse(figures=figures)


@app.get("/api/figures/{figure_path:path}")
def get_figure(figure_path: str):
    figures_root = (Path(__file__).resolve().parent.parent / "model" / "figures").resolve()
    target = (figures_root / figure_path).resolve()
    if not target.is_relative_to(figures_root) or not target.is_file() or target.suffix.lower() != ".png":
        raise HTTPException(status_code=404, detail="Figure not found")
    return FileResponse(target, media_type="image/png")


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

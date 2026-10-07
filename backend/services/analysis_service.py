import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.schemas.api_models import JobMarketResponse, JobMarketSummary


class AnalysisService:
    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = artifacts_dir or Path(__file__).resolve().parents[2] / "model" / "artifacts"

    @property
    def summary_path(self) -> Path:
        return self.artifacts_dir / "job_market_summary.json"

    def get_job_market_summary(self) -> JobMarketResponse:
        if not self.summary_path.is_file():
            return JobMarketResponse(
                status="artifact_missing",
                detail="Job market summary artifact is not available yet.",
            )

        try:
            with self.summary_path.open("r", encoding="utf-8") as file:
                payload: Any = json.load(file)
            summary = JobMarketSummary.model_validate(payload)
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, TypeError, ValueError):
            return JobMarketResponse(
                status="artifact_invalid",
                detail="Job market summary artifact is invalid or unreadable.",
            )
        return JobMarketResponse(status="ready", summary=summary)

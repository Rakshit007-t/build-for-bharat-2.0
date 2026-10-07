from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ReadinessStatus = Literal["ready", "artifact_missing", "artifact_invalid"]
ModelStatus = Literal["ready", "artifact_missing", "artifact_invalid"]


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ComponentReadiness(BaseModel):
    status: ReadinessStatus
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    analysis: ComponentReadiness
    models: dict[str, ComponentReadiness]


class ModelMetadata(BaseModel):
    model_name: str
    model_version: str
    training_rows: int | None = Field(default=None, ge=0)
    feature_names: list[str]
    validation_metrics: dict[str, float] = Field(default_factory=dict)
    selected_threshold: float | None = None


class ModelInfo(BaseModel):
    status: ModelStatus
    target: str
    metadata: ModelMetadata | None = None
    detail: str | None = None


class ModelsResponse(BaseModel):
    jds: ModelInfo
    sds: ModelInfo


class JobMarketSummary(BaseModel):
    total_jobs: int = Field(ge=0)
    top_roles: list[dict[str, Any]]
    top_skills: list[dict[str, Any]]
    salary_summary: dict[str, Any]
    experience_summary: dict[str, Any]
    locations: list[dict[str, Any]]
    generated_from: list[str]
    generated_at: datetime


class JobMarketResponse(BaseModel):
    status: Literal["ready", "artifact_missing", "artifact_invalid"]
    summary: JobMarketSummary | None = None
    detail: str | None = None


class JdsPredictionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    big_data_skills: float = Field(allow_inf_nan=False)
    maths_stats_skills: float = Field(allow_inf_nan=False)
    coding_skills: float = Field(allow_inf_nan=False)
    ai_and_ml_skills: float = Field(allow_inf_nan=False)
    dashboard_and_storytelling_skills: float = Field(allow_inf_nan=False)


class SdsPredictionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    neuroticism: float = Field(allow_inf_nan=False)
    extraversion: float = Field(allow_inf_nan=False)
    openness_to_experience: float = Field(allow_inf_nan=False)
    agreeableness: float = Field(allow_inf_nan=False)
    conscientiousness: float = Field(allow_inf_nan=False)


class PredictionResponse(BaseModel):
    status: Literal["ready", "artifact_missing", "artifact_invalid"]
    prediction: Literal["high", "low"] | None = None
    target: str
    model: ModelMetadata | None = None
    detail: str | None = None

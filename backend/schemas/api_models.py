from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    algorithm: str | None = None
    target: str | None = None
    class_labels: list[str] = Field(default_factory=list)
    class_balance: dict[str, int] = Field(default_factory=dict)
    class_label_interpretation: str | None = None
    confusion_matrix: dict[str, Any] = Field(default_factory=dict)
    model_comparison: dict[str, Any] = Field(default_factory=dict)
    feature_ranges: dict[str, dict[str, float]] = Field(default_factory=dict)
    feature_importance: dict[str, float] = Field(default_factory=dict)
    preprocessing_steps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    cv_folds: int | None = None


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
    dataset_row_counts: dict[str, int] = Field(default_factory=dict)
    top_roles: list[dict[str, Any]]
    top_skills: list[dict[str, Any]]
    skill_vocabulary: list[dict[str, Any]] = Field(default_factory=list)
    top_locations: list[dict[str, Any]] = Field(default_factory=list)
    top_companies: list[dict[str, Any]] = Field(default_factory=list)
    top_skill_pairs: list[dict[str, Any]] = Field(default_factory=list)
    salary_summary: dict[str, Any]
    experience_summary: dict[str, Any]
    locations: list[dict[str, Any]]
    generated_from: list[str]
    generated_at: datetime
    notable_relationships: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    by_dataset: dict[str, Any] = Field(default_factory=dict)


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
    status: Literal["ready", "artifact_missing", "artifact_invalid", "validation_error"]
    prediction: str | None = None
    target: str
    model: ModelMetadata | None = None
    detail: str | None = None


class DashboardSummaryResponse(BaseModel):
    status: Literal["ready", "partial", "not_ready"]
    dataset_row_counts: dict[str, int] = Field(default_factory=dict)
    job_market: JobMarketSummary | None = None
    models: dict[str, dict[str, Any]] = Field(default_factory=dict)
    important_limitations: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None


class FigureItem(BaseModel):
    name: str
    path: str


class FiguresResponse(BaseModel):
    figures: list[FigureItem]


TalentSkill = Literal["python", "sql", "machine_learning", "statistics", "big_data", "dashboard_storytelling"]


class TalentProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[TalentSkill] = Field(min_length=1, max_length=6)

    @field_validator("skills")
    @classmethod
    def skills_are_unique(cls, value: list[TalentSkill]) -> list[TalentSkill]:
        if len(value) != len(set(value)):
            raise ValueError("Select each skill only once.")
        return value


class TalentSkillEvidence(BaseModel):
    skill: TalentSkill
    label: str
    matched: bool
    frequency: int
    supporting_terms: list[str] = Field(default_factory=list)


class TalentRoleMatch(BaseModel):
    role: str
    role_frequency: int
    overlap_percent: float
    matched_skills: list[str]
    role_skill_rule: list[str]


class TalentProfileResponse(BaseModel):
    title: Literal["Descriptive job-market alignment"]
    analysis_type: Literal["descriptive_overlap"]
    overlap_percent: float
    profile_skill_count: int
    matched_skills: list[TalentSkillEvidence]
    unmatched_profile_skills: list[TalentSkillEvidence]
    missing_high_demand_skills: list[dict[str, Any]]
    top_role_categories: list[TalentRoleMatch]
    explanation: str
    role_matching_note: str
    skill_frequency_note: str
    limitations: list[str]

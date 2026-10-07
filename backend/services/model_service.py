import json
import math
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.schemas.api_models import ModelInfo, ModelMetadata, ModelsResponse, PredictionResponse


MODEL_SPECS = {
    "jds": {
        "artifact": "jds_model.pkl",
        "metadata": "jds_metadata.json",
        "target": "salary_hike_high_or_low",
        "features": [
            "big_data_skills",
            "maths_stats_skills",
            "coding_skills",
            "ai_and_ml_skills",
            "dashboard_and_storytelling_skills",
        ],
    },
    "sds": {
        "artifact": "sds_model.pkl",
        "metadata": "sds_metadata.json",
        "target": "success_classification_high_low",
        "features": [
            "neuroticism",
            "extraversion",
            "openness_to_experience",
            "agreeableness",
            "conscientiousness",
        ],
    },
}


@dataclass
class LoadedModel:
    model: Any
    metadata: ModelMetadata


class ModelService:
    """Lazy loader for trusted, locally produced pickle models and JSON metadata."""

    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = artifacts_dir or Path(__file__).resolve().parents[2] / "model" / "artifacts"
        self._cache: dict[str, tuple[tuple[int, int, int, int], LoadedModel]] = {}

    def _paths(self, model_key: str) -> tuple[Path, Path]:
        spec = MODEL_SPECS[model_key]
        return self.artifacts_dir / spec["artifact"], self.artifacts_dir / spec["metadata"]

    def _load(self, model_key: str) -> tuple[LoadedModel | None, str | None, str | None]:
        spec = MODEL_SPECS[model_key]
        model_path, metadata_path = self._paths(model_key)
        if not model_path.is_file() or not metadata_path.is_file():
            return None, "artifact_missing", "Model artifact or metadata is not available yet."

        try:
            model_stat = model_path.stat()
            metadata_stat = metadata_path.stat()
            signature = (
                model_stat.st_mtime_ns,
                model_stat.st_size,
                metadata_stat.st_mtime_ns,
                metadata_stat.st_size,
            )
            cached = self._cache.get(model_key)
            if cached and cached[0] == signature:
                return cached[1], None, None

            with metadata_path.open("r", encoding="utf-8") as file:
                metadata_payload = json.load(file)
            if "training_rows" not in metadata_payload or not metadata_payload.get("class_labels"):
                raise ValueError("Model metadata is missing required training_rows or class_labels.")
            metadata = ModelMetadata.model_validate(metadata_payload)
            if metadata.feature_names != spec["features"]:
                raise ValueError("Model metadata feature_names do not match the integration contract.")
            if metadata.target != spec["target"]:
                raise ValueError("Model metadata target does not match the integration contract.")
            if any(not math.isfinite(value) for value in metadata.validation_metrics.values()):
                raise ValueError("Model metadata contains a non-finite validation metric.")
            for name, bounds in metadata.feature_ranges.items():
                if name not in spec["features"] or set(bounds) != {"min", "max"}:
                    raise ValueError("Model metadata contains an invalid feature range.")
                if not all(math.isfinite(value) for value in bounds.values()) or bounds["min"] > bounds["max"]:
                    raise ValueError("Model metadata contains an invalid feature range.")

            # Artifacts are produced locally by the team. Never load user-supplied pickle files.
            with model_path.open("rb") as file:
                model = pickle.load(file)
            if not callable(getattr(model, "predict", None)):
                raise ValueError("Loaded artifact does not expose a predict method.")
            loaded = LoadedModel(model=model, metadata=metadata)
            self._cache[model_key] = (signature, loaded)
            return loaded, None, None
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, pickle.UnpicklingError, EOFError, AttributeError, ImportError, TypeError, ValueError):
            self._cache.pop(model_key, None)
            return None, "artifact_invalid", "Model artifact or metadata is invalid or could not be loaded."
        except Exception:
            self._cache.pop(model_key, None)
            return None, "artifact_invalid", "Model artifact failed to load."

    def get_models(self) -> ModelsResponse:
        values: dict[str, ModelInfo] = {}
        for key, spec in MODEL_SPECS.items():
            loaded, status, detail = self._load(key)
            values[key] = ModelInfo(
                status="ready" if loaded else status,
                target=spec["target"],
                metadata=loaded.metadata if loaded else None,
                detail=detail,
            )
        return ModelsResponse(**values)

    def get_readiness(self) -> dict[str, dict[str, str | None]]:
        readiness = {}
        for key in MODEL_SPECS:
            loaded, status, detail = self._load(key)
            readiness[key] = {"status": "ready" if loaded else status, "detail": detail}
        return readiness

    def predict(self, model_key: str, features: dict[str, float]) -> PredictionResponse:
        spec = MODEL_SPECS[model_key]
        missing = [name for name in spec["features"] if name not in features]
        if missing:
            return PredictionResponse(
                status="validation_error",
                target=spec["target"],
                detail="Prediction input is missing required features.",
            )

        loaded, status, detail = self._load(model_key)
        if loaded is None:
            return PredictionResponse(status=status, target=spec["target"], detail=detail)

        for name in spec["features"]:
            observed_range = loaded.metadata.feature_ranges.get(name)
            value = float(features[name])
            if observed_range and not (observed_range["min"] <= value <= observed_range["max"]):
                return PredictionResponse(
                    status="validation_error",
                    target=spec["target"],
                    model=loaded.metadata,
                    detail=f"Feature '{name}' is outside the observed training range.",
                )

        try:
            values = [[float(features[name]) for name in spec["features"]]]
            raw_prediction = loaded.model.predict(values)
            if len(raw_prediction) != 1:
                raise ValueError("Model returned an unexpected number of predictions.")
            prediction = str(raw_prediction[0]).strip().lower()
            allowed_labels = {label.strip().lower() for label in loaded.metadata.class_labels}
            if prediction not in allowed_labels:
                raise ValueError("Model prediction does not match a class label declared in metadata.")
        except Exception:
            return PredictionResponse(
                status="artifact_invalid",
                target=spec["target"],
                model=loaded.metadata,
                detail="Model could not produce a valid prediction for this input.",
            )

        return PredictionResponse(
            status="ready",
            prediction=prediction,
            target=spec["target"],
            model=loaded.metadata,
        )

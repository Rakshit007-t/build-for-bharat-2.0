from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.src.cleaning import clean_frame
from model.src.config import (
    ARTIFACTS_DIR,
    DATASETS,
    DATA_REPORTS_DIR,
    FIGURES_DIR,
    JDS_FEATURES,
    MODEL_REPORTS_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    SDS_FEATURES,
    TARGETS,
)
from model.src.io import audit_frame, load_dataset, standardize_column_name, write_json
from model.src.jds_model import train_jds
from model.src.job_market import analyze_job_sources
from model.src.reporting import build_approach_note, write_data_quality_reports, write_job_market_report
from model.src.sds_model import train_sds


def _directories() -> None:
    for path in (RAW_DIR, PROCESSED_DIR, DATA_REPORTS_DIR, RAW_DIR.parent / "figures", ARTIFACTS_DIR, FIGURES_DIR, MODEL_REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)
    (FIGURES_DIR / "job_market").mkdir(parents=True, exist_ok=True)


def _load_all() -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    loaded: dict[str, pd.DataFrame] = {}
    quality: dict[str, Any] = {"generated_at": datetime.now(timezone.utc).isoformat(), "datasets": {}}
    for key, filename in DATASETS.items():
        path = RAW_DIR / filename
        if not path.is_file():
            quality["datasets"][key] = {"status": "missing", "expected_path": str(path.relative_to(RAW_DIR.parent.parent))}
            continue
        try:
            frame = load_dataset(path)
            loaded[key] = frame
            quality["datasets"][key] = {"status": "loaded", "audit": audit_frame(frame, filename)}
        except Exception as exc:
            quality["datasets"][key] = {"status": "invalid", "error": f"{type(exc).__name__}: {exc}"}
    quality["status"] = "complete" if len(loaded) == len(DATASETS) else "partial"
    return loaded, quality


def _resolve_columns(frame: pd.DataFrame, expected: list[str], target: str) -> dict[str, str]:
    normalized = {standardize_column_name(column): column for column in frame.columns}
    # Common punctuation variants are resolved by name normalization, preserving semantics.
    mapping: dict[str, str] = {}
    for name in expected + [target]:
        actual = normalized.get(standardize_column_name(name))
        if actual:
            mapping[name] = actual
    return mapping


def _run_model(key: str, frame: pd.DataFrame, features: list[str], target: str, trainer, report: dict[str, Any]) -> dict[str, Any]:
    mapping = _resolve_columns(frame, features, target)
    missing = [name for name in features + [target] if name not in mapping]
    if missing:
        result = {"status": "not_trainable", "reason": "Required fields were not present after column normalization.", "missing_fields": missing, "available_columns": list(frame.columns)}
        write_json(result, MODEL_REPORTS_DIR / f"{key}_training.json")
        report["datasets"][key]["model_status"] = result
        return result

    work = frame.rename(columns={actual: canonical for canonical, actual in mapping.items()}).copy()
    cleaned, cleaning = clean_frame(work, f"{key}_traits")
    write_json(cleaning, DATA_REPORTS_DIR / f"{key}_cleaning.json")
    cleaned.to_csv(PROCESSED_DIR / f"{key}_traits_cleaned.csv", index=False)
    result = trainer(cleaned, ARTIFACTS_DIR)
    write_json(result, MODEL_REPORTS_DIR / f"{key}_training.json")
    report["datasets"][key]["cleaning"] = cleaning
    report["datasets"][key]["model_status"] = {"status": result.get("status"), "reason": result.get("reason")}
    return result


def _write_final_status(quality: dict[str, Any], job_summary: dict[str, Any] | None, model_results: dict[str, Any]) -> None:
    lines = ["# Final Project Status", "", f"Pipeline status: **{quality['status']}**", f"Generated: {quality['generated_at']}", "", "## Datasets", ""]
    for name, entry in quality.get("datasets", {}).items():
        audit = entry.get("audit", {})
        lines.append(f"- {name}: {audit.get('rows', 'not available')} rows, {audit.get('columns', 'not available')} columns, {audit.get('missing_cells', 'not available')} missing cells, {audit.get('duplicate_rows', 'not available')} exact duplicates.")
    lines += ["", "## Selected models and measured validation", ""]
    for key in ("jds", "sds"):
        result = model_results.get(key, {})
        if result.get("status") == "ready":
            metrics = ", ".join(f"{name}={value:.4f}" for name, value in result["validation_metrics"].items() if isinstance(value, (int, float)))
            lines.append(f"- {key.upper()}: {result['model_name']} ({result['algorithm']}); {result['training_rows']} complete cases; {result['cv_folds']}-fold stratified out-of-fold validation; {metrics}. Target labels preserved as `{', '.join(result['class_labels'])}` because the numeric code mapping is undocumented.")
        else:
            lines.append(f"- {key.upper()}: {result.get('status', 'not ready')}; {result.get('reason', 'No valid artifact available.')}")
    lines += ["", "## Job-market findings", ""]
    if job_summary:
        lines.append(f"- {job_summary['total_jobs']:,} source rows across both job files; `reported_job_count_total`={job_summary['reported_job_count_total']:,} using source `num_of_jobs` plus one per Analytics Jobs row, not a deduplicated market estimate.")
        if job_summary.get("top_skills"):
            lines.append("- Top skill mentions: " + ", ".join(f"{item['name']} ({item['count']:,})" for item in job_summary["top_skills"][:8]) + ".")
        if job_summary.get("top_roles"):
            lines.append("- Top role rows: " + ", ".join(f"{item['name']} ({item['count']:,})" for item in job_summary["top_roles"][:8]) + ".")
        if job_summary.get("top_locations"):
            lines.append("- Top location components: " + ", ".join(f"{item['name']} ({item['count']:,})" for item in job_summary["top_locations"][:8]) + ".")
        for name, relationship in job_summary.get("notable_relationships", {}).items():
            lines.append(f"- Salary/experience association in {name}: r={relationship['pearson_r']:.4f}, n={relationship['paired_rows']}; descriptive only.")
    else:
        lines.append("- Job-market summary is not available.")
    lines += ["", "## Cleaning summary", "", "All four files were read without changing `data/raw/`. Column names/text were normalized, numeric salary/experience fields were added where interpretable, skill text was tokenized, and exact duplicates were removed only in derived frames with indices recorded. Inspect `data/reports/data_quality_report.json` for per-field details.", "", "## API endpoints", "", "`GET /health`, `GET /api/readiness`, `GET /api/models`, `GET /api/analysis/job-market`, `GET /api/reports/summary`, `GET /api/figures`, `GET /api/figures/{path}`, `POST /api/models/jds/predict`, and `POST /api/models/sds/predict`.", "", "## Run the prototype", "", "```powershell", "python -m venv .venv", ".venv\\Scripts\\activate", "python -m pip install -r requirements.txt", "python model\\src\\run_pipeline.py", "python model\\src\\generate_approach_docx.py", "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000", "```", "", "Open `http://127.0.0.1:8000/`.", "", "## Demo flow", "", "1. Open overview and show readiness, row counts, and actual source aggregates.", "2. Show job roles, skill mentions, salary/experience coverage and data caveats.", "3. Show cross-validated model comparisons and limitations.", "4. Enter clearly labeled demo inputs within the artifact's observed feature ranges; show the predicted encoded source class.", "5. Explain that encoded class meanings were not documented, cross-validation is not external validation, and the SDS analysis is not a hiring score.", "", "## Limitations", "", "- Small trait datasets and no external validation.", "- Numeric target mappings to semantic high/low are unavailable.", "- Job sources are not a labor-market census; salary units/periods vary or are unspecified.", "- Observational associations do not establish causality.", "- SDS predictions must not be used to screen or rank candidates.", "", "## Files to show judges", "", "`docs/APPROACH_NOTE.md`, `docs/APPROACH_NOTE.docx`, `data/reports/data_quality_report.md`, `data/reports/job_market_report.md`, `model/reports/jds_training.json`, `model/reports/sds_training.json`, `model/figures/`, `backend/main.py`, and the local dashboard.", ""]
    (Path(__file__).resolve().parents[2] / "FINAL_STATUS.md").write_text("\n".join(lines), encoding="utf-8")


def run_pipeline() -> int:
    _directories()
    loaded, quality = _load_all()
    for key, frame in loaded.items():
        frame.to_csv(PROCESSED_DIR / f"{key}_standardized.csv", index=False)

    job_result = None
    job_keys = {"analytics_jobs", "datascience_jobs"}
    if job_keys.issubset(loaded):
        job_result = analyze_job_sources(
            {key: loaded[key] for key in ("analytics_jobs", "datascience_jobs")},
            DATA_REPORTS_DIR,
            FIGURES_DIR / "job_market",
        )
        write_json(job_result["summary"], ARTIFACTS_DIR / "job_market_summary.json")
        write_job_market_report(job_result, DATA_REPORTS_DIR / "job_market_report.md")
        quality["job_market"] = {
            "status": "ready",
            "row_counts": job_result["summary"]["dataset_row_counts"],
            "cleaning": {name: value for name, value in zip(job_result["summary"]["dataset_row_counts"], job_result["cleaning_reports"])},
        }
        for name, clean in zip(job_result["summary"]["dataset_row_counts"], job_result["cleaning_reports"]):
            quality["datasets"][name]["cleaning"] = clean
    else:
        quality["job_market"] = {"status": "not_ready", "missing_datasets": sorted(job_keys - set(loaded))}

    model_results: dict[str, Any] = {}
    if "jds" in loaded:
        model_results["jds"] = _run_model("jds", loaded["jds"], JDS_FEATURES, TARGETS["jds"], train_jds, quality)
    else:
        model_results["jds"] = {"status": "not_ready", "reason": "JDS Skill Traits.xlsx is missing."}
    if "sds" in loaded:
        model_results["sds"] = _run_model("sds", loaded["sds"], SDS_FEATURES, TARGETS["sds"], train_sds, quality)
    else:
        model_results["sds"] = {"status": "not_ready", "reason": "SDS Personality Traits.xlsx is missing."}

    write_data_quality_reports(quality, DATA_REPORTS_DIR)
    note = build_approach_note(quality, job_result["summary"] if job_result else None, model_results)
    docs_dir = Path(__file__).resolve().parents[2] / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "APPROACH_NOTE.md").write_text(note, encoding="utf-8")
    write_json({"generated_at": datetime.now(timezone.utc).isoformat(), "status": quality["status"], "datasets": quality["datasets"], "job_market": quality.get("job_market"), "models": {key: {"status": value.get("status"), "model_name": value.get("model_name"), "validation_metrics": value.get("validation_metrics"), "reason": value.get("reason")} for key, value in model_results.items()}}, MODEL_REPORTS_DIR / "pipeline_status.json")
    _write_final_status(quality, job_result["summary"] if job_result else None, model_results)

    missing_files = [entry.get("expected_path", entry.get("error", "input file invalid")) for entry in quality["datasets"].values() if entry["status"] != "loaded"]
    if missing_files:
        print("Pipeline completed with missing input datasets:")
        for filename in missing_files:
            print(f"  - {filename}")
        print("No results were fabricated. Add the organizer files under data/raw/ and rerun.")
        return 2
    print("Local pipeline complete. See data/reports/, model/reports/, and model/artifacts/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_pipeline())

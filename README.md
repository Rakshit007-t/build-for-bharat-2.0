# Ghost Skills — Workforce Intelligence Prototype

Ghost Skills locally analyzes the four organizer-provided Build for Bharat datasets: two job-posting files, JDS Skill Traits, and SDS Personality Traits. It includes a reproducible Python pipeline, evaluated tabular models where the labels support validation, a local FastAPI API, a responsive static dashboard, and generated reports.

## Privacy and interpretation

- Raw files, derived analysis, model training, and inference stay on the local machine. The API serves aggregates and model outputs, never raw dataset rows.
- No Gemini, OpenAI, external AI APIs, remote fonts, or third-party frontend scripts are used.
- Job-market results describe the supplied posting sources, not the whole labor market.
- Predictions concern only the labels present in the supplied files. Cross-validation is internal validation, not external validation.
- Observational skill/personality patterns do not establish causation. SDS output is not universal personality-based hiring truth or an individual hiring score.
- Missing inputs, ambiguous targets, and unusable artifacts are reported; results are never fabricated.

## Windows quickstart

Use Python 3.10 or newer. Place the organizer files locally at these exact paths:

```text
data\raw\Analytics Jobs.csv
data\raw\DataScience Jobs.csv
data\raw\JDS Skill Traits.xlsx
data\raw\SDS Personality Traits.xlsx
```

Then run from the repository root in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python model\src\run_pipeline.py
python model\src\generate_approach_docx.py
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. The pipeline writes cleaning and analysis reports, figures, model artifacts/metadata where valid, and `docs/APPROACH_NOTE.md`. The second command creates `docs/APPROACH_NOTE.docx` with the report and generated figures. If a dataset is missing or a model target is not validatable, the pipeline records that state instead of making up output.

## Regenerate and verify

```powershell
# Rebuild processed data, descriptive summaries, models, figures, and Approach Note
python model\src\run_pipeline.py

# Run local tests
python -m pytest -q

# API health and generated summaries
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/readiness
Invoke-RestMethod http://127.0.0.1:8000/api/reports/summary
Invoke-RestMethod http://127.0.0.1:8000/api/models
```

Install dependencies once while online; subsequent pipeline, API, and dashboard use is local. The dashboard itself has no runtime CDN or external service dependency.

## Outputs

- `data/processed/`: standardized and cleaned derived CSV files; `data/raw/` is read-only.
- `data/reports/data_quality_report.*`: schema, row counts, missingness, duplicates, and cleaning audit.
- `data/reports/job_market_report.md`: source-aware descriptive findings.
- `model/artifacts/`: local job-market summary and model pickle/JSON metadata only when valid.
- `model/figures/`: generated job-market and model evaluation figures.
- `model/reports/`: per-model evaluation details and pipeline status.
- `docs/APPROACH_NOTE.md` / `.docx`: generated from actual available results. If inputs are missing, the document states that and contains no fabricated findings.
- `docs/PRESENTATION_OUTLINE.md`, `docs/DEMO_SCRIPT.md`, `docs/JUDGE_QA.md`: presentation materials.

## API endpoints

- `GET /health`, `GET /api/health`
- `GET /api/readiness`
- `GET /api/analysis/job-market`
- `GET /api/models`
- `POST /api/models/jds/predict`
- `POST /api/models/sds/predict`
- `POST /api/talent/profile` (descriptive skill overlap, not a trained prediction)
- `GET /api/reports/summary`
- `GET /api/figures` and `GET /api/figures/{relative_figure_path}`

For exact feature names and artifacts, see [MODEL_INTEGRATION_CONTRACT.md](MODEL_INTEGRATION_CONTRACT.md). For end-to-end scope and order, see [MASTER_BUILD_PLAN.md](MASTER_BUILD_PLAN.md). `PLAN.md` and `API_CONTRACT.md` describe the current dataset-driven prototype.

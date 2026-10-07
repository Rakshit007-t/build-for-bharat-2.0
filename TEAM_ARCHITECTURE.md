# Standalone Build Architecture

This workspace is now built as a standalone prototype. A single local pipeline reads the organizer datasets and produces analysis artifacts, models, reports, and figures. No teammate handoff is required to run it.

## Local flow

```text
data/raw (read-only organizer files)
  -> model/src local ingestion, cleaning, analysis and evaluation
  -> data/processed + reports + model/artifacts + model/figures
  -> backend FastAPI local-only service
  -> frontend static dashboard
  -> Approach Note and presentation materials from generated results
```

## Folder ownership for this standalone build

| Folder | Purpose |
| --- | --- |
| `data/raw/` | Local organizer inputs; never edited or committed |
| `data/processed/` | Reproducible standardized/cleaned tables |
| `data/reports/` | Data-quality and job-market reports |
| `model/src/` | Ingestion, cleaning, EDA, models, evaluation and report generation |
| `model/artifacts/` | Locally produced model files, metadata, aggregate market summary |
| `model/figures/` | Generated local PNG charts |
| `backend/` | FastAPI routes and safe local artifact loading |
| `frontend/` | Static HTML/CSS/vanilla JS dashboard |
| `docs/` | Objective, Approach Note, demo, presentation and judge Q&A |

## Analytics scope

- Descriptive job-market intelligence from Analytics Jobs and DataScience Jobs.
- JDS technical features predicting only the supplied salary-hike label, if valid data supports stratified evaluation. Preserve encoded 0/1 classes unless their semantic mapping is documented.
- SDS traits predicting only the supplied organizational success label, with explicit association and non-hiring-use caveats.

No causal conclusions, invented labels, synthetic result data, fabricated predictions, or fake performance metrics. If data or artifacts are unavailable, API and report outputs identify the missing state.

See [MASTER_BUILD_PLAN.md](MASTER_BUILD_PLAN.md) for implementation order and [MODEL_INTEGRATION_CONTRACT.md](MODEL_INTEGRATION_CONTRACT.md) for artifact format and API integration details.

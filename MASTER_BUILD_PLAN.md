# Ghost Skills — Master Build Plan

**Operating mode:** standalone local build. This workspace executes the complete pipeline without waiting for a three-person handoff. All analysis and inference use the organizer-provided files in `data/raw/`; raw rows must not leave this machine.

## Product and analysis objective

Analyze job-market demand, technical skill outcomes, and workforce-trait labels to produce transparent workforce intelligence. The work separates descriptive summaries from predictions, associations from causation, and business implications from observed findings. No fabricated data, labels, predictions, metrics, or claims are acceptable.

## Data-to-demo architecture

```text
data/raw (four organizer files; read-only)
  -> model/src local ingestion, audits, cleaning, analysis, stratified CV
  -> data/reports + data/processed + model/artifacts + model/figures + model/reports
  -> backend FastAPI loads aggregate JSON and trusted local pickle models
  -> frontend vanilla JS dashboard reads localhost API only
  -> result-based Approach Note, presentation materials, and final status
```

## Repository deliverables

- `model/src/`: reproducible local ingestion, cleaning, job-market analysis, model evaluation, and report generation.
- `data/raw/`: organizer inputs only; never written by the pipeline.
- `data/processed/`: standardized/cleaned derived tables.
- `data/reports/`: data quality and job-market reports.
- `model/artifacts/`: model pickle files, metadata, and job-market aggregate JSON.
- `model/figures/`: computed figures only.
- `backend/`: localhost API; no dataset rows exposed.
- `frontend/`: offline-capable static dashboard; no third-party scripts.
- `docs/`: problem statement, analytics objective, result-based Approach Note, presentation outline, demo script, and judge Q&A.

## Build sequence

1. **Input gate:** Confirm all four organizer files are present, readable, and unchanged. Record dimensions, columns, missingness, and duplicates.
2. **Preparation:** Normalize names and text; add parsed salary/experience and skill fields; record exact duplicate removal and all transformations. Never silently drop rows.
3. **Job-market analysis:** Analyze both posting files, generate source-specific and combined aggregates, relationship checks, and a concise set of figures.
4. **JDS model:** Verify exact features and encoded target classes; compare majority baseline, logistic regression, and random forest with stratified CV; preserve undocumented numeric class codes and save out-of-fold metrics plus an all-data serving model only when each class supports CV.
5. **SDS model:** Apply the same evaluation process to the supplied success label; explicitly limit interpretation to within-sample association and prohibit hiring use.
6. **Integration:** Validate real artifacts via API, return clean missing/invalid states, and keep raw records private.
7. **Dashboard:** Render only API-derived facts and generated figures, display model limitations, and label predictor inputs as user-entered demo values.
8. **Documentation:** Generate the Approach Note and DOCX after actual runs; prepare an explicitly timed talk track and judge Q&A. Do not claim results before artifacts exist.
9. **Quality gate:** Run tests, execute the full pipeline, start the local server, smoke-test all routes and a prediction, check JavaScript, verify the static app, and inspect report outputs.

## Current input blocker

At the last inventory, `data/raw/` and all four organizer files were absent. The pipeline and docs must report this as an input blocker and must not create empty or synthetic result artifacts. Place these files in `data/raw/` before treating the submission as complete:

- `Analytics Jobs.csv`
- `DataScience Jobs.csv`
- `JDS Skill Traits.xlsx`
- `SDS Personality Traits.xlsx`

## Technical constraints

- No Gemini, OpenAI, external AI APIs, cloud processing, remote fonts, or third-party frontend scripts.
- Local Python, pandas, openpyxl, NumPy, scikit-learn, matplotlib, FastAPI, and python-docx only.
- Any saved model is only as valid as its supplied target; never remap ambiguous class labels.
- Job posting counts are source-specific and descriptive. Salary comparisons retain source currency and exclude ambiguous values.
- Cross-validation is not external validation. Small samples and potential label/sample bias must be disclosed.

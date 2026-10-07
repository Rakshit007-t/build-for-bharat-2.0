# Final Project Status

Pipeline status: **complete**
Generated: 2026-10-07T09:53:56.371915+00:00

## Datasets

- analytics_jobs: 15841 rows, 8 columns, 15520 missing cells, 0 exact duplicates.
- datascience_jobs: 1602 rows, 8 columns, 0 missing cells, 0 exact duplicates.
- jds: 139 rows, 7 columns, 0 missing cells, 0 exact duplicates.
- sds: 161 rows, 7 columns, 0 missing cells, 0 exact duplicates.

## Selected models and measured validation

- JDS: JDS Logistic Regression (logistic_regression); 139 complete cases; 5-fold stratified out-of-fold validation; accuracy=0.8345, precision_macro=0.8343, recall_macro=0.8337, f1_macro=0.8340, roc_auc=0.8924. Target labels preserved as `0, 1` because the numeric code mapping is undocumented.
- SDS: SDS Random Forest (random_forest); 161 complete cases; 5-fold stratified out-of-fold validation; accuracy=0.9565, precision_macro=0.9567, recall_macro=0.9560, f1_macro=0.9564, roc_auc=0.9949. Target labels preserved as `0, 1` because the numeric code mapping is undocumented.

## Job-market findings

- 17,443 source rows across both job files; `reported_job_count_total`=108,846 using source `num_of_jobs` plus one per Analytics Jobs row, not a deduplicated market estimate.
- Top skill mentions: analytics (1,048), sql (1,009), python (938), finance (811), java (752), business analysis (730), machine learning (724), data analysis (721).
- Top role rows: Business Analyst (296), Data Scientist (252), Data Analyst (237), Data Engineer (207), Senior Business Analyst (206), Senior Data Scientist (199), Senior Data Analyst (195), Senior Data Engineer (184).
- Top location components: Bengaluru (4,108), Mumbai (2,643), Gurgaon (2,129), Delhi NCR (1,363), Pune (1,253), Hyderabad (1,179), Chennai (1,083), Noida (682).
- Salary/experience association in datascience_jobs: r=0.5933, n=1602; descriptive only.

## Cleaning summary

All four files were read without changing `data/raw/`. Column names/text were normalized, numeric salary/experience fields were added where interpretable, skill text was tokenized, and exact duplicates were removed only in derived frames with indices recorded. Inspect `data/reports/data_quality_report.json` for per-field details.

## API endpoints

`GET /health`, `GET /api/readiness`, `GET /api/models`, `GET /api/analysis/job-market`, `GET /api/reports/summary`, `GET /api/figures`, `GET /api/figures/{path}`, `POST /api/models/jds/predict`, and `POST /api/models/sds/predict`.

## Run the prototype

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python model\src\run_pipeline.py
python model\src\generate_approach_docx.py
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`.

## Demo flow

1. Open overview and show readiness, row counts, and actual source aggregates.
2. Show job roles, skill mentions, salary/experience coverage and data caveats.
3. Show cross-validated model comparisons and limitations.
4. Enter clearly labeled demo inputs within the artifact's observed feature ranges; show the predicted encoded source class.
5. Explain that encoded class meanings were not documented, cross-validation is not external validation, and the SDS analysis is not a hiring score.

## Limitations

- Small trait datasets and no external validation.
- Numeric target mappings to semantic high/low are unavailable.
- Job sources are not a labor-market census; salary units/periods vary or are unspecified.
- Observational associations do not establish causality.
- SDS predictions must not be used to screen or rank candidates.

## Files to show judges

`docs/APPROACH_NOTE.md`, `docs/APPROACH_NOTE.docx`, `data/reports/data_quality_report.md`, `data/reports/job_market_report.md`, `model/reports/jds_training.json`, `model/reports/sds_training.json`, `model/figures/`, `backend/main.py`, and the local dashboard.

# Final Project Status

Pipeline status: **complete**
Generated: 2026-10-07T11:49:10.535387+00:00

## Datasets

- analytics_jobs: 15841 rows, 8 columns, 15520 missing cells, 0 exact duplicates.
- datascience_jobs: 1602 rows, 8 columns, 0 missing cells, 0 exact duplicates.
- jds: 139 rows, 7 columns, 0 missing cells, 0 exact duplicates.
- sds: 161 rows, 7 columns, 0 missing cells, 0 exact duplicates.

## Selected models and measured validation

- JDS: not ready; No valid artifact available.
- SDS: not ready; No valid artifact available.

## Job-market findings

- 17,443 job-posting source rows across both job files. DataScience Jobs separately reports 93,005 source `num_of_jobs` volume; this is not a deduplicated market estimate.
- Top skill mentions: analytics (1,048), sql (1,009), python (938), finance (811), java (752), business analysis (730), machine learning (724), data analysis (721).
- Role frequency — Analytics Jobs source rows: Business Analyst (108), Data Scientist (64), Data Analyst (50), Digital Marketing Manager (45), Home Base Job/ Data Entry/online Work/part Time Work/freelancer work (45), Product Manager (44), Digital Marketing Executive (36), Analyst (35).
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

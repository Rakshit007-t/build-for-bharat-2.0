# Final Project Status

Pipeline status: **complete**
Generated from the four organizer-provided datasets; raw source files remain local and unchanged.

## Datasets and analysis

- Analytics Jobs: 15,841 rows, 8 columns, 15,520 missing cells, 0 exact duplicates.
- DataScience Jobs: 1,602 rows, 8 columns, 0 missing cells, 0 exact duplicates.
- JDS Skill Traits: 139 rows, 7 columns, 0 missing cells, 0 exact duplicates; target codes 0=66, 1=73.
- SDS Personality Traits: 161 rows, 7 columns, 0 missing cells, 0 exact duplicates; target codes 0=76, 1=85.
- Job files contain 17,443 source rows. The reported count total (108,846) sums source `num_of_jobs` plus one per Analytics Jobs row; it is not deduplicated and is not a market-size estimate.
- Most frequent normalized skill mentions include analytics (1,048), SQL (1,009), Python (938), finance (811), Java (752), business analysis (730), machine learning (724), and data analysis (721). Counts are mentions, not unique people or jobs.
- Top role rows: Business Analyst (296), Data Scientist (252), Data Analyst (237), Data Engineer (207).
- Top location components: Bengaluru (4,108), Mumbai (2,643), Gurgaon (2,129), Delhi NCR (1,363), Pune (1,253).
- DataScience Jobs salary/experience association: Pearson r=0.5933, n=1,602; descriptive only.
- Source files have differing aggregation structures and no row-level join key. Job-market statistics are not a census. Skill frequencies come from Analytics Jobs `key_skills`, since DataScience Jobs has no extracted skill field.

## Selected models and measured validation

Metrics are stratified 5-fold out-of-fold estimates on small datasets, not external validation. Numeric labels remain encoded as 0/1 because semantic target mapping is undocumented.

- JDS: Logistic Regression, 139 rows; accuracy 0.8345, macro precision 0.8343, macro recall 0.8337, macro F1 0.8340, ROC-AUC 0.8924; confusion matrix [[54,12],[11,62]].
- SDS: Random Forest, 161 rows; accuracy 0.9565, macro precision 0.9567, macro recall 0.9560, macro F1 0.9564, ROC-AUC 0.9949; confusion matrix [[72,4],[3,82]].
- The SDS model is exploratory and must not be used to screen or rank people. Neither model establishes causation.

## Prototype and API

The local FastAPI app serves the dashboard, dataset-based job-market summaries, model metadata, prediction endpoints, and a talent profile exploration endpoint. The talent endpoint accepts clearly labeled user-entered demo skills, reports descriptive vocabulary overlap and missing frequent skills, and provides analyst-authored heuristic role suggestions. It is not a learned role-fit model, hiring probability, or person score. Skill frequency is sourced only from Analytics Jobs `key_skills`.

Endpoints: `GET /health`, `GET /api/readiness`, `GET /api/models`, `GET /api/analysis/job-market`, `GET /api/reports/summary`, `GET /api/figures`, `GET /api/figures/{path}`, `POST /api/models/jds/predict`, `POST /api/models/sds/predict`, and `POST /api/talent/profile`.

Run locally with `.venv\Scripts\activate`, then `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`; open `http://127.0.0.1:8000/`. Data preparation/training and report generation use the scripts in `model/src/`.

## Demo flow

1. Show readiness, source row counts, and data-quality caveats.
2. Explore role, location, skill mentions, and salary/experience descriptives.
3. Show model comparisons and explain encoded targets and cross-validation limits.
4. Submit clearly labeled demo values and show encoded class outputs only.
5. Enter demo skills in Talent Intelligence; distinguish descriptive overlap from heuristic suggestions.
6. Explain small sample sizes, missing semantic label mapping, no external validation, no causal claims, and no candidate screening use.

## Deliverables and verification

- Approach Note: `docs/APPROACH_NOTE.md` and `docs/APPROACH_NOTE.docx` (21-page main note plus a 7-page generated-figures appendix; 28 pages total in Word PDF export QA).
- Demo script: `docs/DEMO_SCRIPT.md`; presentation outline: 20 slides / about 9:40; judge Q&A: `docs/JUDGE_QA.md`.
- Dashboard includes Overview, Job Market, JDS, SDS, Talent Intelligence, Predict, and Methodology views.
- Verification: 28 tests passed; Python compileall passed; `node --check frontend/app.js` passed; `git diff --check` passed; all 19 generated figures and application routes were smoke-tested locally.
- All organizer data processing is local; raw/derived row-level datasets are ignored by Git. No external AI/API dependency is used.

## Limitations

Small trait datasets; no external validation; undocumented semantic meaning of encoded targets; job sources are not a labor-market census; salary units/periods may be unspecified; observational relationships do not establish causation; talent suggestions are analyst-authored heuristics; SDS outputs are not suitable for hiring decisions.

## Files to show judges

`docs/APPROACH_NOTE.md`, `docs/APPROACH_NOTE.docx`, `data/reports/data_quality_report.md`, `data/reports/job_market_report.md`, `model/reports/jds_training.json`, `model/reports/sds_training.json`, `model/figures/`, `backend/main.py`, and the local dashboard.

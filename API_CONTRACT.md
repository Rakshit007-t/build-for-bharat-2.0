# Ghost Skills Local API Contract

Base URL: `http://127.0.0.1:8000`. Responses are JSON except PNG figure responses. The service reads only generated aggregate JSON and trusted local model artifacts; raw organizer rows are never served.

## Readiness and summaries

- `GET /health` and `GET /api/health` → `{ "status": "ok" }` for process health.
- `GET /api/readiness` → overall status plus analysis/JDS/SDS component states (`ready`, `artifact_missing`, or `artifact_invalid`).
- `GET /api/analysis/job-market` → actual summary when valid, or a not-ready/invalid status with no invented numbers.
- `GET /api/models` → target, artifact status, model metadata and measured evaluation metrics. Does not expose per-row training data.
- `GET /api/reports/summary` → dashboard-safe aggregated source row counts, market summary, model names/metrics, limitations, and generation time.
- `GET /api/figures` → local PNG figure names and API paths.
- `GET /api/figures/{relative_figure_path}` → a generated PNG contained under `model/figures/`; all other paths return 404.
- `POST /api/talent/profile` → descriptive overlap against the normalized aggregate skill vocabulary, missing top-demand terms, and up to five heuristic role suggestions with source role frequencies. It does not read or expose raw rows and does not call a trained model.

Talent profile request:

```json
{"skills": ["python", "sql", "machine_learning"]}
```

Allowed skill IDs: `python`, `sql`, `machine_learning`, `statistics`, `big_data`, `dashboard_storytelling`. Select one to six distinct skills. The result's overlap percent is the share of selected categories with at least one term in the aggregate skill vocabulary. Skill frequencies come from Analytics Jobs `key_skills`; DataScience Jobs has no extracted skill field. Role suggestions use analyst-authored title-to-skill rules because there is no row-level join key or role-by-skill cross-tab; they are not observed per-role skill matches or hiring probabilities.

## Prediction requests

`POST /api/models/jds/predict` accepts finite numeric values for:

```json
{
  "big_data_skills": 0,
  "maths_stats_skills": 0,
  "coding_skills": 0,
  "ai_and_ml_skills": 0,
  "dashboard_and_storytelling_skills": 0
}
```

`POST /api/models/sds/predict` accepts finite numeric values for:

```json
{
  "neuroticism": 0,
  "extraversion": 0,
  "openness_to_experience": 0,
  "agreeableness": 0,
  "conscientiousness": 0
}
```

The zeros above demonstrate request field types only; they are not recommended or observed values. Frontend controls use measured feature ranges from metadata when available. Invalid/missing/out-of-range fields return a structured `validation_error` (HTTP 422 for malformed fields; HTTP 200 application response for values outside artifact ranges). A well-formed request with no valid model returns HTTP 200 with `artifact_missing` or `artifact_invalid` and a null prediction. Success returns `status: ready` and the encoded class returned by the model. The supplied target codes are 0/1 and their high/low mapping is undocumented, so the API preserves those codes. No probability is implied.

For exact file names, formats, feature order, and metadata requirements see [MODEL_INTEGRATION_CONTRACT.md](MODEL_INTEGRATION_CONTRACT.md).

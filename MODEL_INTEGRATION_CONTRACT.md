# Model Integration Contract

This is the handoff contract between Person A (local data/model work) and Person B (backend). It does not prescribe an algorithm. All files stay local during the hackathon. The backend loads only locally produced artifacts from `model/artifacts/` and does not read source datasets.

## Artifact layout and format

```text
model/artifacts/
├── jds_model.pkl
├── jds_metadata.json
├── sds_model.pkl
├── sds_metadata.json
└── job_market_summary.json
```

Model files use Python pickle serialization and must expose a `predict(rows)` method that accepts a two-dimensional, single-row list in the exact feature order below. Only load artifacts produced and trusted locally; pickle files can execute code when loaded. Do not commit organizer datasets.

Metadata is a UTF-8 JSON object validated against this shape:

```json
{
  "model_name": "",
  "model_version": "",
  "algorithm": "",
  "training_rows": null,
  "feature_names": [],
  "target": "",
  "class_labels": [],
  "validation_metrics": {},
  "selected_threshold": null,
  "preprocessing_steps": [],
  "feature_ranges": {},
  "limitations": [],
  "created_at": ""
}
```

`training_rows` is a non-negative integer or null while unknown. `feature_names` must exactly match the corresponding ordered list below. `validation_metrics` contains only measured numeric metrics; leave it empty until evaluation exists. `selected_threshold` is a measured numeric threshold or null when not applicable. Do not put placeholder/fabricated metric numbers in metadata.

The local build additionally records the selected algorithm, target, allowed class labels, preprocessing steps, observed feature ranges, limitations, and creation timestamp. Model metadata responses include the training-row count for transparent evaluation context; dashboard summary responses expose aggregate source counts and metrics only.

## JDS model

- Model: `model/artifacts/jds_model.pkl`
- Metadata: `model/artifacts/jds_metadata.json`
- Target: `salary_hike_high_or_low`
- Ordered features:
  1. `big_data_skills`
  2. `maths_stats_skills`
  3. `coding_skills`
  4. `ai_and_ml_skills`
  5. `dashboard_and_storytelling_skills`
- The current source stores the target as encoded numeric labels. The model preserves the observed labels (currently `0` and `1`) in metadata and returns the predicted encoded label. Do not map these to “high”/“low” until organizer documentation confirms the encoding.

## SDS model

- Model: `model/artifacts/sds_model.pkl`
- Metadata: `model/artifacts/sds_metadata.json`
- Target: `success_classification_high_low`
- Ordered features:
  1. `neuroticism`
  2. `extraversion`
  3. `openness_to_experience`
  4. `agreeableness`
  5. `conscientiousness`
- The current source stores the target as encoded numeric labels. The model preserves the observed labels (currently `0` and `1`) in metadata and returns the predicted encoded label. Do not map these to “high”/“low” until organizer documentation confirms the encoding.

Person A must document the meaning, scale, and allowed input range of each feature based on the supplied data before the frontend presents an input control. Backend numeric validation rejects non-finite values but does not assume a scale. This predictive interface does not imply that personality causes success or is suitable for individual hiring decisions.

## Job-market summary artifact

Person A may provide `model/artifacts/job_market_summary.json` with this structure:

```json
{
  "job_posting_source_rows": 0,
  "reported_job_volume_total": 0,
  "reported_job_volume_note": "DataScience Jobs num_of_jobs volume is reported separately from posting source rows.",
  "analytics_role_frequency": [],
  "datascience_role_frequency": [],
  "datascience_reported_job_volume": [],
  "top_skills": [],
  "salary_summary": {},
  "experience_summary": {},
  "locations": [],
  "generated_from": [],
  "generated_at": "2026-01-01T00:00:00Z"
}
```

The zero and empty containers above describe field types only; they are not dataset results. `job_posting_source_rows` is the sum of Analytics Jobs and DataScience Jobs source rows. `analytics_role_frequency` counts Analytics Jobs source role rows; `datascience_role_frequency` counts DataScience Jobs role-label source rows; `datascience_reported_job_volume` and `reported_job_volume_total` use the DataScience Jobs `num_of_jobs` field. Keep these measures separate: the sources use different counting structures, and source rows are not unique vacancies. `generated_from` lists the source dataset filenames, and `generated_at` is an ISO 8601 timestamp. Skill, location, salary, and experience summaries must reflect actual local analysis and include the units/definitions needed to interpret them.

## Backend status behavior

- Missing model or metadata: `artifact_missing`; no prediction is returned.
- Malformed metadata, incompatible feature names, unreadable/corrupt artifact, or model errors: `artifact_invalid`; no prediction is returned.
- Successful prediction: `ready` with the encoded source class and validated model metadata. The API does not invent a high/low class mapping or probabilities.
- Missing/invalid job-market summary: `artifact_missing` / `artifact_invalid`; no synthetic summary is returned.

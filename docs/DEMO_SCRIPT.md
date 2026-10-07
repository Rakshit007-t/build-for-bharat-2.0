# 10-Minute Demo Script

## 0:00–1:00 — Problem and objective

Introduce Ghost Skills as a local workforce-intelligence prototype. State the distinction between describing job-posting data and modeling the labels supplied in the two traits datasets. Clarify that the project does not claim causality or rank candidates.

## 1:00–2:00 — Data and preparation

Show the four local source files and the data quality report. Explain actual row counts, missingness, duplicates, parsing rules, and any fields that could not be interpreted. Do not display row-level personal or sensitive data.

## 2:00–4:00 — Job-market intelligence

Open the market view. Show actual role and skill aggregates and one salary/experience figure. Explain source coverage, currency/parseability caveats, and that postings are not a labor-market census.

## 4:00–6:00 — JDS model

Show target balance, baseline/model comparison, out-of-fold metrics, confusion matrix, and feature interpretation. Explain the fold strategy and sample-size limitation. Run a prediction only if the real artifact is ready; label the entered values as demo inputs.

## 6:00–7:30 — SDS model

Show the supplied target, evaluation, and feature interpretation. State clearly that the model describes association with this dataset’s label and is not universal personality-based hiring truth or a causal claim.

## 7:30–8:30 — Architecture and privacy

Show the local data → pipeline → artifacts → API → dashboard flow. Confirm raw data stays local and API routes expose aggregates rather than rows.

## 8:30–10:00 — Conclusions and Q&A

State only findings present in the generated reports. Close with limitations, additional validation needed, and stakeholder implications as proposed next steps.

**If artifacts are missing:** demonstrate readiness/error handling and explicitly state which source or model result was not available. Do not substitute sample predictions.

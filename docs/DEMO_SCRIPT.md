# Ghost Skills: exact 3-minute demo

Use the local dashboard at `http://127.0.0.1:8000/`. Confirm the API is running and the real artifacts are ready before the judges arrive. Do not use row-level data on screen. The profile below is an explicitly demo-entered set of skills, not a real candidate record.

## 0:00–0:20 — Problem and objective

“Teams need a clearer view of advertised analytics skills and of what the supplied outcome datasets can—and cannot—support. Ghost Skills turns four organizer datasets into local job-market analysis and two separate, internally evaluated classifiers. Descriptive findings and predictions stay distinct.”

## 0:20–0:50 — Supplied datasets and quality

Open **Methodology** and show the four data sources and audit report. State the observed rows: Analytics Jobs 15,841; DataScience Jobs 1,602; JDS 139; SDS 161. Mention 15,520 missing cells in Analytics Jobs, mostly job type and description, and that no exact duplicate rows were detected. The raw files remain local; show only aggregate quality information.

## 0:50–1:20 — Job-market insight

Open **Job market**. Point to the normalized skill-mention counts: Python 938, SQL 1,009, and Machine Learning 724. Show leading roles (Business Analyst 296, Data Scientist 252) and locations (Bengaluru 4,108, Mumbai 2,643). Say these are mentions and source-row counts, not unique people, deduplicated vacancies, or a labor-market census. The job files have different aggregation structures and no row-level join key.

## 1:20–1:50 — Talent Intelligence profile

Open **Talent Intelligence**. Select Python, SQL, Machine Learning, Statistics, Big Data, and Dashboard / Storytelling, then submit. Explain the descriptive vocabulary overlap, mention frequencies, missing top-demand skills, and heuristic role suggestions. Read the visible caveat: “This is a descriptive overlap analysis based on supplied job-posting data; it is not a hiring probability.” Role suggestions use explicit title-to-skill rules because the source has no role-by-skill cross-tab. Do not describe this as a trained prediction or candidate score.

## 1:50–2:20 — JDS model

Open **Technical skills** and show the selected JDS model, 139 complete cases, five-fold stratified cross-validation, actual metrics, baseline comparison, confusion matrix, and coefficient-magnitude figure. Explain that the prediction is an encoded class because the 0/1 mapping is undocumented. If time permits, open **Predict**, enter values within the displayed observed ranges, and say they are demo inputs.

## 2:20–2:40 — SDS model and responsible AI

Open **Workforce traits**. Show the selected model and its validation summary. Point to the high-visibility warning: “This exploratory association model is not a hiring score and must not be used to screen individuals.” The output preserves encoded labels and is not a statement about an individual's success.

## 2:40–3:00 — Conclusion

“The prototype connects local data preparation, descriptive analysis, validated local models, an API, and an actionable skill-overlap exploration. The output is useful for framing workforce questions; it is not an employment decision system.” Close with: **“Data → analysis → validated local model → actionable workforce intelligence.”**

## Recovery notes

- If readiness is not `ready`, explain the missing local artifact and do not invent a result.
- If a figure fails, use the summary figures in `model/figures/` and report the UI issue honestly.
- If a model prediction is unavailable or outside its observed input range, show the validation message and continue.
- No step requires external connectivity.

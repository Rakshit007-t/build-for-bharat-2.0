# Ghost Skills local resume verification

## What it does

The verification workflow accepts PDF and TXT resumes (or explicitly entered resume text), extracts selectable text locally with `pypdf` for PDFs, and applies deterministic phrase matching. Supported MVP skills are Python, SQL, and Machine Learning. Level aliases map only to Beginner, Intermediate, or Advanced when explicit text is nearby; otherwise the claim is `Unspecified`. The API does not return the full stored resume text.

Resume excerpts are literal lines from the resume that include a supported skill and a relevant action/context term. The report shows those excerpts so a user can inspect what was matched. Project and certification section summaries use actual bullet lines in those sections.

## Evidence heuristic

The **Prototype heuristic evidence score** awards points for distinct matching resume excerpts, with per-category caps:

| Category | Points per excerpt | Cap |
|---|---:|---:|
| Relevant project | 20 | 40 |
| Work or internship experience | 12.5 | 25 |
| Certification | 15 | 15 |
| Tool or implementation evidence | 10 | 20 |

The total is already normalized to 0–100. This rule is deterministic and explainable, but it is not scientifically validated, does not authenticate credentials, and should not be treated as objective proof of skill.

## Assessment and result calculation

Question banks live under `content/questions/`; each skill has two easy, two medium, and two hard multiple-choice questions. A session asks three questions, begins at medium, increases difficulty after a correct answer, and decreases difficulty after an incorrect answer. Difficulty weights are easy 1, medium 2, hard 3. Test score is the weighted correct points divided by all question weights, expressed as a percentage. The answer key remains server-side.

`final score = evidence score × 0.4 + test score × 0.6`

Bands are `<40 Beginner`, `40–70 Intermediate`, and `>70 Advanced`. Explicit claims are compared to the resulting band to label `confirmed`, `underclaimed`, or `overclaimed`. If no level was explicitly stated, the result is `unverified`, with no forced verified-level classification.

## Local persistence and privacy

Candidate metadata, extracted resume text, claims, evidence, assessment answers, and results persist in `data/local/verification.sqlite3`. The database stays on the machine and is excluded from Git. No external AI, API, or remote service is called by this feature. Keep uploaded resume files and database outside source control.

## Synthetic demo profiles

Files in `content/samples/` are fictional synthetic resumes, not organizer data or real candidates. The overclaimed Python demo starts with no concrete supporting evidence and can produce an overclaim when answers are missed. The underclaimed profile combines intermediate claims with substantial project/work evidence; strong assessment answers can lift its result to Advanced. The confirmed profile is designed for intermediate claims and a plausible mixed answer path. Results are computed from claims, excerpts, and actual answers; no result is hardcoded.

## Limitations

- Extraction is phrase-based and can miss unusual wording, multi-column PDF ordering, scanned/image-only PDFs, or context split across lines.
- Evidence points count matched text, not verified work or credentials. A resume may be inaccurate.
- The assessment is a short prototype quiz, not a validated test. Small question banks allow repeated exposure.
- Final bands and status are product heuristics, not employment outcomes or causal findings.
- Job-market alignment reuses existing aggregate job-posting analysis. It describes vocabulary overlap and role rules, not a candidate-fit score or employment probability.
- Nothing in the workflow is a hiring decision or suitability recommendation.

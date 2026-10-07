# Ghost Skills — 20-slide presentation outline

**Target duration: 9 minutes 40 seconds** (average 29 seconds per slide). Use only current local report values and generated figures. The role/skill profile is a descriptive heuristic, not a predictive or hiring score.

| # | Slide | Suggested evidence / speaking point | Time |
|---:|---|---|---:|
| 1 | Problem | Fragmented views of advertised demand and supplied workforce outcome labels. | 0:20 |
| 2 | Analytics objective | Separate description, encoded-label prediction, association, and implications. | 0:25 |
| 3 | Why the supplied data matters | Four organizer sources make a local, reproducible prototype possible. | 0:25 |
| 4 | Four datasets | Two job-posting sources; JDS skills; SDS personality traits. | 0:30 |
| 5 | Data-quality audit | Actual row counts, missingness, duplicates, and target balance. | 0:30 |
| 6 | Preparation | Local normalization, audit trail, conservative salary parsing, no fabricated labels. | 0:30 |
| 7 | Job-market findings | 17,443 job-posting source rows; different source aggregation structures. | 0:25 |
| 8 | Skill demand | Python 938, SQL 1,009, Machine Learning 724 normalized mentions. | 0:30 |
| 9 | Roles and locations | Analytics Jobs role frequency: Business Analyst 108 source role rows; DataScience Jobs reported Business Analyst volume: 32,843 `num_of_jobs`; Bengaluru 4,108; Mumbai 2,643. Measures use different source structures and stay separate. | 0:30 |
| 10 | JDS modelling | 139 complete labeled rows; compare majority baseline, logistic regression, random forest. | 0:30 |
| 11 | JDS validation | Five-fold stratified out-of-fold metrics and confusion matrix. | 0:35 |
| 12 | JDS interpretation | Coefficient magnitude visualization; encoded 0/1 meaning not supplied. | 0:25 |
| 13 | SDS modelling | 161 complete labeled rows; same simple candidate-model comparison. | 0:30 |
| 14 | SDS validation | Five-fold metrics, baseline, and confusion matrix. | 0:35 |
| 15 | Responsible AI limitation | Exploratory association model is not a hiring score; never screen individuals. | 0:35 |
| 16 | Talent Intelligence prototype | Profile skills, normalized mention overlap, missing skills, heuristic role suggestions. | 0:40 |
| 17 | Business implications | Use aggregate demand to frame training and workforce-planning questions. | 0:25 |
| 18 | Limitations | No join key, non-census postings, small samples, no external validation, unknown target mapping. | 0:35 |
| 19 | Conclusion | Data → analysis → validated local model → actionable workforce intelligence. | 0:25 |
| 20 | Q&A | Invite questions; keep the local dashboard ready for evidence. | 0:20 |

**Total: 9:40.** If time is short, reduce slides 4–6 and 10–14 while keeping the target-code and responsible-use caveats.

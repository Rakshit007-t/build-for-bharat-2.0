# Judge Q&A

Answers reflect the current local implementation and supplied data. Do not expand them into claims the data cannot support.

## 1. Why these models?

We compare a majority-class baseline, scaled logistic regression, and random forest using stratified out-of-fold predictions. These are practical tabular baselines; selection uses macro F1, then accuracy as a tie-break—not training-set fit.

## 2. Why no deep learning?

The labeled tables have only 139 JDS and 161 SDS complete cases and structured numeric features. Deep learning would add complexity without resolving small-sample uncertainty or undocumented labels.

## 3. Why only 139/161 labelled rows?

Those are the complete-case rows in the supplied JDS and SDS datasets after numeric coercion for the five features and target. No records or labels were synthesized. The original files contain 139 and 161 rows respectively, with no audited missing cells.

## 4. Why use cross-validation?

Five-fold shuffled stratified cross-validation uses the limited rows for both fitting and out-of-fold evaluation while preserving class proportions. It estimates internal performance only; it is not an independent or external validation set.

## 5. Why is SDS accuracy so high?

On these 161 rows, the selected random forest reached 0.9565 accuracy and 0.9564 macro F1 in five-fold out-of-fold evaluation, versus a 0.3455 majority-baseline macro F1. This may reflect strong separation within this particular sample or how the supplied label and features were constructed. The sample is small, no external validation exists, and the result should not be generalized without independent replication.

## 6. What does 0/1 actually mean?

The files store numeric target codes 0 and 1. The available source materials do not provide an authoritative mapping from those codes to “high” or “low”, so the models and UI preserve them as encoded labels.

## 7. Why didn’t you infer the high/low mapping?

Inferring it from class frequency or feature associations would invent label meaning and risk reversing interpretation. We need an authoritative codebook from the data owner.

## 8. Why combine datasets without joining them?

The two job files have different fields and aggregation structures, and there is no row-level join key. The system presents side-by-side aggregates, not a record-level merge. The Talent Intelligence role suggestions are explicitly analyst-authored title/skill heuristics; they are not observed role-by-skill co-occurrence.

## 9. How is the system useful to recruiters?

The job-posting aggregates and descriptive skill-overlap workflow can help frame workforce-planning, role-profile, and training questions. They are not candidate ranking, hiring probability, or decision support for an individual.

## 10. Does personality predict performance?

This prototype only estimates the dataset’s supplied encoded label from its supplied trait fields. The label is not established here as independently verified job performance or universal success. No employment decisions should use this model.

## 11. Are you making causal claims?

No. Job counts are descriptive, model outputs are predictions of supplied labels, and observed associations do not establish that a skill or personality trait causes an outcome.

## 12. How do you address bias?

We do not claim bias is eliminated. The small files do not support a meaningful fairness audit across groups. We expose limitations, avoid candidate scoring, and require representative data, label review, subgroup evaluation, external validation, and governance before any operational use.

## 13. What happens with more data?

First confirm label definitions and consent/provenance. Then collect representative, well-defined outcome data, reserve independent and temporal validation sets, test subgroup performance and drift, and reassess whether every feature is appropriate for the intended use.

## 14. Why not use an LLM?

The objective is aggregate analysis and small tabular classification. A local deterministic Python pipeline is easier to reproduce and keeps organizer data on-device. No external AI service is needed or called.

## 15. How do you protect the supplied datasets?

Raw organizer files and row-level processed files stay local and are ignored by Git. The API exposes aggregate reports, model metadata, figures, and predictions, not raw rows. The prototype has no external API integration. Keep the server bound to localhost for the demo.

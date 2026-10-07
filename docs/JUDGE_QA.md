# Judge Q&A

## Why these models?

Logistic regression and random forest provide contrasting, reproducible baselines for tabular classification. A majority-class classifier anchors performance. Selection is based on stratified out-of-fold metrics, not training fit alone.

## Why these datasets?

They are the four organizer-provided datasets and cover postings, recorded skill outcomes, and a supplied organizational success label. Each supports a different evidence type and is analyzed separately.

## Why not deep learning?

The data are structured tabular data and may be small. Simpler models are easier to validate and interpret; deep learning would not solve label quality or representativeness limits.

## How did you validate?

The pipeline uses shuffled stratified cross-validation when each class has enough observations, compares against a majority baseline, and reports out-of-fold metrics. This remains internal validation, not external generalization evidence.

## Why such a small dataset?

The prototype is constrained to the supplied files. Exact row counts and class balance are reported after loading the actual data; no additional or synthetic records are introduced.

## Does personality really predict success?

The model can only test whether the recorded traits associate with the dataset’s supplied label under internal validation. It does not establish universal predictive validity or causation and is not a hiring score.

## Are you claiming causality?

No. Job-market counts are descriptive; skill and trait models estimate supplied labels. Observational associations do not show causal effects.

## What does the job-market dataset add?

It provides aggregate views of skills, roles, locations, experience, and parseable salary records across the two supplied posting sources, with source-coverage limitations.

## How is this useful to recruiters?

The job-posting summaries can inform workforce-planning questions. The experimental classifiers are research prototypes and should not drive individual candidate decisions.

## How would this scale?

Future work would require documented data contracts, representative samples, external validation, monitored drift, privacy review, and a governed local or approved deployment. Scaling cannot remove sample or label bias.

## How do you prevent bias?

The prototype does not claim bias is eliminated. It exposes limitations, avoids candidate scoring, and requires future subgroup checks, label review, and representative external validation before any operational use.

## What would you do with more data?

Collect consented, representative, well-defined and independently validated outcome data; replicate job-market analysis across time and sources; then test robustness, subgroup performance, and drift.

# Team Architecture — Build for Bharat 2.0

## Product direction

Build a local analytics prototype from the four organizer-provided SAS datasets. The analysis covers job-market intelligence from Analytics Jobs and DataScience Jobs, technical skill outcome prediction from JDS Skill Traits, and secondary personality/success analysis from SDS Personality Traits. Dataset-derived findings and model predictions must be presented separately. These observational datasets do not establish causation. Do not invent labels, ground truth, results, or metrics; clearly label any user-entered/demo values.

All dataset access, preparation, analysis, training, and inference stay local during the hackathon. Do not upload dataset content to external AI services, APIs, cloud services, or third parties.

## Ownership and folders

| Person | Ownership | Main folders / deliverables |
| --- | --- | --- |
| **Person A** | Dataset inventory, preprocessing, EDA, statistical/ML analysis and evaluation, job-market analysis, saved model and analysis artifacts | `model/` |
| **Person B** | FastAPI backend, API layer, integration of Person A's locally produced outputs | `backend/` |
| **Person C** | Frontend dashboard, presentation, and Approach Note based on actual analysis and results | `frontend/`, presentation, Approach Note |

The supplied datasets should remain local and should not be committed unless the team explicitly agrees that repository storage is appropriate. Person B does not modify `model/`; Person C does not modify `frontend/` outside their ownership. Coordinate any shared contract changes before implementation.

## Integration points

- **Person A → Person B:** Agree a small, documented artifact contract: artifact filenames/paths, feature and target definitions, preprocessing assumptions, model version, output fields, evaluation metrics, and known limitations. Supply serialized model/preprocessing artifacts only when the chosen analysis supports prediction. Also provide reproducible descriptive summaries for dashboard use.
- **Person B → Person C:** Agree API routes and JSON response shapes before wiring the UI. Serve descriptive job-market aggregates and analysis metadata separately from prediction requests/results. Include metric and provenance fields where relevant, and return clear unavailable/error states when artifacts or results are not ready.
- **Person C → Person A/B:** Share the dashboard's required views and fields early; base Approach Note claims on the completed analysis, evaluated results, conclusions, and implications.

## Data and serving flow

```text
Four organizer datasets (local)
  -> Person A: local data preparation and EDA
  -> Person A: descriptive/statistical analysis and evaluated ML where justified
  -> saved model/preprocessing artifacts and analysis summaries
  -> Person B: local FastAPI endpoints load/serve those outputs
  -> Person C: frontend dashboard presents summaries and clearly labeled predictions
```

The job-market views are descriptive. The JDS technical-skill work may expose predictions only if a defensible target, evaluation, and saved artifact exist. SDS personality/success analysis is secondary and should be presented as an association/analysis, not a causal or individual hiring verdict. No unsupported inference should be presented as ground truth.

## Explicitly out of scope for this 12-hour sprint

- Resume verification, resume/GitHub ingestion, adaptive testing, candidate scoring, and the previous Gemini-driven product plan.
- Sending datasets or derived row-level data to external services; adding external AI dependencies.
- Inventing labels, synthetic results, evaluation metrics, or unsupported causal conclusions.
- Training or prediction without checking whether the supplied data supports a meaningful target and evaluation.
- Broad production infrastructure, authentication, deployment, or nonessential features that do not support the dataset-driven demo.

## Next 12-hour milestone order

1. **Align and inventory:** Confirm the four supplied files, schemas, access constraints, and analysis questions; agree the artifact and API contracts.
2. **Prepare and explore:** Person A profiles, cleans, and documents the data locally; produces EDA and data-quality findings.
3. **Analyze and evaluate:** Complete job-market summaries, technical-skill analysis/modeling only where justified, and secondary SDS analysis; record actual results and limitations.
4. **Freeze integration outputs:** Person A saves documented artifacts/summaries and evaluation details; Person B confirms the backend contract and locally loads the available outputs.
5. **Integrate dashboard:** Person B implements the API layer; Person C connects the dashboard to agreed endpoints and distinguishes descriptive results from predictions/demo inputs.
6. **Reconcile and present:** Check the end-to-end prototype against actual artifacts, clarify limitations, and have Person C write the Approach Note and presentation from the observed analysis and results.

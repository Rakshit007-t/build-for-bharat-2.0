# Ghost Skills — Build for Bharat 2.0

> A local, dataset-driven analytics prototype using the four organizer-provided SAS datasets.

## Product direction

The prototype focuses on three dataset-backed analyses:

- Job-market intelligence using the Analytics Jobs and DataScience Jobs datasets.
- Technical-skill outcome analysis and prediction using JDS Skill Traits, where the available data supports a defensible target and evaluation.
- Secondary personality/success analysis using SDS Personality Traits.

Analysis and inference stay local during the hackathon. Descriptive findings are distinct from model predictions. The datasets do not establish causation; the project will not invent ground truth or metrics. Any user-entered or demo values must be labeled clearly. See [TEAM_ARCHITECTURE.md](TEAM_ARCHITECTURE.md) for ownership, integration, scope, and milestones.

## Team ownership

| Team member | Ownership | Focus |
| --- | --- | --- |
| **Person A** | `model/` | Local data preparation, EDA, analysis/modeling/evaluation, job-market analysis, saved artifacts |
| **Person B** | `backend/` | FastAPI API layer and integration of Person A's local outputs |
| **Person C** | `frontend/`, presentation, Approach Note | Dashboard, presentation, and documentation based on actual results |

`PLAN.md` and `API_CONTRACT.md` currently describe an earlier resume-verification scaffold and should not be treated as the current product requirements. Agree updated integration contracts before implementation.

## Local development

The repository is currently an initial scaffold. Install the Python dependencies in `requirements.txt` in a local environment, then run the API with:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

The health endpoint is at `http://localhost:8000/health`; the static frontend is served at `http://localhost:8000/`.

## Repository layout

```text
ghost-skills/
├── backend/             # Person B: local FastAPI API and integration
├── frontend/            # Person C: dashboard
├── model/               # Person A: local analysis, training, and artifacts (to be added)
├── content/             # Existing empty scaffold directories
├── TEAM_ARCHITECTURE.md # Current sprint ownership, integration, and milestones
├── PLAN.md              # Earlier product plan; superseded for this sprint
└── API_CONTRACT.md      # Earlier API contract; update with team agreement
```

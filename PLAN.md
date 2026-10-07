# Ghost Skills - 21-Hour Hackathon Execution Plan

## 1. Product Summary
Ghost Skills is an AI-powered skill verification layer for technical hiring. Candidates submit a resume (PDF/text) from which Gemini extracts claimed technical competencies and claimed proficiency levels (Beginner, Intermediate, Advanced). An evidence engine cross-references the resume and optional GitHub activity (0–100 score), followed by a 5-question adaptive diagnostic test (0–100 score). The final composite score (`0.4 * evidence + 0.6 * test`) objectively classifies each MVP skill (Python, SQL, Machine Learning) as Confirmed, Underclaimed, or Overclaimed, surfacing hidden gems and flagging resume exaggeration.

## 2. Architecture & Ownership
### Ownership
- **Person A (Backend)**: `backend/` (FastAPI app, Gemini prompt chains, SQLite persistence, scoring algorithms, test execution engine).
- **Person B (Frontend & Content)**: `frontend/` (single-page Tailwind app, upload, adaptive test UI, candidate report view) & `content/` (question banks, schema samples, demo resumes).

### Folder Structure
```
ghost-skills/
├── backend/          # Person A: FastAPI app, DB, Gemini clients, scoring
├── frontend/         # Person B: Single-page HTML/Tailwind/vanilla JS app
├── content/          # Person B: Curated question banks & test resumes
│   ├── questions/    # python.json, sql.json, ml.json
│   └── samples/      # resume_sample.pdf, candidate_demo.json
├── API_CONTRACT.md   # Shared interface contract (frozen)
└── PLAN.md           # Master roadmap & schema
```

### Text Data Flow
```
[Resume PDF/Text] ──> [POST /api/upload] ──> [Gemini Extraction] ──> [SQLite: candidates, candidate_skills]
         │                                                                     │
         ▼                                                                     ▼
[Optional GitHub] ──> [POST /github]    ──> [GitHub Scraper/Gemini] ──> [Update evidence_score]
         │                                                                     │
         ▼                                                                     ▼
[Adaptive Test]   ──> [GET /next, POST /answer] ──> [Gemini Evaluator] ──> [Update test_score]
         │                                                                     │
         ▼                                                                     ▼
[Report & Insights] <── [GET /report] <── [0.4*Evidence + 0.6*Test] <── [Status Classifier]
```

## 3. SQLite Database Schema
```sql
CREATE TABLE candidates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    raw_resume TEXT,
    github_username TEXT,
    projects_json TEXT DEFAULT '[]',
    certifications_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE candidate_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL REFERENCES candidates(id),
    skill TEXT NOT NULL, -- 'Python', 'SQL', 'Machine Learning'
    claimed_level TEXT NOT NULL, -- 'Beginner', 'Intermediate', 'Advanced'
    evidence_score REAL DEFAULT 0,
    test_score REAL DEFAULT 0,
    final_score REAL DEFAULT 0,
    verified_level TEXT,
    status TEXT, -- 'confirmed', 'underclaimed', 'overclaimed'
    explanation TEXT,
    evidence_snippets_json TEXT DEFAULT '[]'
);

CREATE TABLE questions (
    id TEXT PRIMARY KEY,
    skill TEXT NOT NULL,
    type TEXT NOT NULL, -- 'mcq', 'code', 'sql', 'scenario'
    difficulty TEXT NOT NULL, -- 'easy', 'medium', 'hard'
    prompt TEXT NOT NULL,
    options_json TEXT,
    starter_code TEXT,
    schema_hint TEXT,
    rubric TEXT NOT NULL
);

CREATE TABLE test_sessions (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidates(id),
    skill TEXT NOT NULL,
    current_index INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 5,
    is_completed INTEGER DEFAULT 0
);

CREATE TABLE test_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES test_sessions(id),
    question_id TEXT NOT NULL REFERENCES questions(id),
    answer TEXT NOT NULL,
    score REAL NOT NULL, -- 0.0 to 1.0
    correct INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 4. 21-Hour Timeline & Milestones
- **H0–H2 (Scaffold & Freeze)**: Freeze API contract, SQLite schema, repo setup. (Both)
- **H2–H8 (Core Pipeline)**:
  - Person A: Resume PDF extraction + Gemini skill parser + initial evidence scoring.
  - Person B: Single-page UI shell (Upload + Claim cards) + seed 15 questions per skill in `content/questions/`.
- **H8–H14 (Adaptive Test & Evaluation)**:
  - Person A: `/test/next` adaptive question selector & `/test/answer` evaluation logic.
  - Person B: Question interaction UI (MCQ selector, code/SQL editor, immediate feedback).
- **H14–H18 (Scoring, Reports & Seed)**:
  - Person A: `0.4*evidence + 0.6*test` formula, classification logic, report endpoint, `/demo` fixture.
  - Person B: Verification badge UI (Confirmed/Under/Over), radar/bar score cards, recruitment dashboard.
- **H18–H21 (End-to-End Polish & Demo Rehearsal)**: Edge cases, loading states, full 3-minute pitch run.

## 5. Verification & Testing Strategy
- Unit tests (`pytest`) covering: scoring formula, level classification boundaries, and API contract shape.
- `GET /api/demo` & `POST /api/reset` guarantees deterministic presentation state without API flake risk.

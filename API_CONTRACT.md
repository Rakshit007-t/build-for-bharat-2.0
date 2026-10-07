# Ghost Skills - API Contract (v1.0)

This document defines the strict REST API contract between **Backend (Person A)** and **Frontend (Person B)**.

---

## 1. Global Conventions & Standards

- **Base URL**: `http://localhost:8000`
- **Default Format**: `application/json` (unless multipart form upload)
- **Levels**: Strictly `"Beginner" | "Intermediate" | "Advanced"`
- **Verification Statuses**: Strictly `"confirmed" | "underclaimed" | "overclaimed"`
- **Question Types**: Strictly `"mcq" | "code" | "sql" | "scenario"`
- **Question Difficulties**: Strictly `"easy" | "medium" | "hard"`
- **Score Scale**:
  - `evidence_score`: `0 - 100` (float or int)
  - `test_score`: `0 - 100` (float or int)
  - `final_score`: `0 - 100` (`final_score = 0.4 * evidence_score + 0.6 * test_score`)
  - `score` in per-question answer: `0.0 - 1.0` (float)
- **Error Format**:
  All non-2xx responses MUST return a JSON object with an `"error"` message string:
  ```json
  {
    "error": "Descriptive human-readable error message"
  }
  ```

---

## 2. Endpoints

### 2.1 POST `/api/upload`
Upload candidate resume as a file (PDF) or as plain text in a form field. AI extracts candidate info, claimed skills, claimed levels, and initial resume evidence snippets.

- **Content-Type**: `multipart/form-data`
- **Request Parameters**:
  - `file` *(optional file)*: Resume PDF document
  - `text` *(optional form field)*: Plain text resume content
  *(Either `file` or `text` must be provided)*

#### Request Example (Multipart Form)
```http
POST /api/upload HTTP/1.1
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="resume.pdf"
Content-Type: application/pdf

[raw pdf bytes]
------WebKitFormBoundary--
```

#### Response (200 OK)
```json
{
  "candidate_id": "cand_9f83a1b2",
  "name": "Alex Mercer",
  "skills": [
    {
      "skill": "Python",
      "claimed_level": "Advanced",
      "evidence_snippets": [
        "Built distributed event streaming pipelines with FastAPI and AsyncIO handling 5M daily events.",
        "Refactored legacy monolith into async microservices improving throughput by 300%."
      ]
    },
    {
      "skill": "SQL",
      "claimed_level": "Intermediate",
      "evidence_snippets": [
        "Authored complex PostgreSQL analytic queries and window functions for executive dashboards.",
        "Reduced p99 query latency from 1.8s to 220ms via composite indexing and explain analyze."
      ]
    },
    {
      "skill": "Machine Learning",
      "claimed_level": "Beginner",
      "evidence_snippets": [
        "Fine-tuned scikit-learn random forest models for customer churn classification."
      ]
    }
  ],
  "projects": [
    "High-throughput Event Ingestion Engine (Python, Kafka)",
    "PostgreSQL Analytics Warehouse Migration",
    "Churn Prediction Pipeline (scikit-learn)"
  ],
  "certifications": [
    "AWS Certified Solutions Architect",
    "DeepLearning.AI Specialization"
  ]
}
```

#### Error Responses
- `400 Bad Request`: `{"error": "Neither 'file' nor 'text' was provided in the upload request"}`
- `422 Unprocessable Entity`: `{"error": "Failed to parse PDF resume text"}`

---

### 2.2 POST `/api/candidates/{id}/github`
Analyze candidate's public GitHub profile to generate supplemental evidence scores and insights per skill.

- **Content-Type**: `application/json`
- **Path Parameter**: `id` (string, e.g. `"cand_9f83a1b2"`)
- **Request Body**:
  ```json
  {
    "username": "alexmercer-dev"
  }
  ```

#### Response (200 OK)
```json
{
  "evidence_breakdown": {
    "Python": {
      "score": 88,
      "details": [
        "14 public repositories with active commits in the last 12 months.",
        "Creator of an async worker utility with 340+ GitHub stars.",
        "Consistent PEP8 compliance, unit tests, and type annotations across projects."
      ]
    },
    "SQL": {
      "score": 72,
      "details": [
        "Found multiple repositories containing migration files, raw SQL scripts, and schema DDLs.",
        "Implemented indexed query patterns and relational joins in backend services."
      ]
    },
    "Machine Learning": {
      "score": 45,
      "details": [
        "Jupyter notebook repos present covering exploratory data analysis.",
        "Basic training scripts found; limited production model deployment code."
      ]
    }
  }
}
```

#### Error Responses
- `400 Bad Request`: `{"error": "GitHub username cannot be empty"}`
- `404 Not Found`: `{"error": "Candidate 'cand_9f83a1b2' not found"}`

---

### 2.3 GET `/api/test/{candidate_id}/{skill}/next`
Fetches the next adaptive question for the given candidate and skill. When all questions for the skill are complete, returns `{ "done": true }`.

- **Path Parameters**:
  - `candidate_id` (string): e.g. `"cand_9f83a1b2"`
  - `skill` (string): e.g. `"Python"`, `"SQL"`, or `"Machine Learning"`

#### Response (200 OK - Active Question)
```json
{
  "question_id": "py_q04",
  "type": "code",
  "prompt": "Write a generator function `chunked(iterable, n)` that yields lists of size `n` from the input sequence.",
  "options": null,
  "starter_code": "def chunked(iterable, n):\n    # TODO: implement generator\n    pass\n",
  "schema_hint": null,
  "difficulty": "medium",
  "index": 2,
  "total": 5,
  "done": false
}
```

#### Response (200 OK - MCQ Question Example)
```json
{
  "question_id": "sql_q01",
  "type": "sql",
  "prompt": "Which window function calculates the running total of `amount` ordered by `created_at`?",
  "options": [
    "SUM(amount) OVER (ORDER BY created_at)",
    "TOTAL(amount) PARTITION BY created_at",
    "LAG(amount) OVER (ORDER BY created_at)",
    "COUNT(amount) OVER (ORDER BY created_at)"
  ],
  "starter_code": null,
  "schema_hint": "Table: orders(id INT, amount NUMERIC, created_at TIMESTAMP)",
  "difficulty": "easy",
  "index": 1,
  "total": 5,
  "done": false
}
```

#### Response (200 OK - When All Questions Completed)
```json
{
  "done": true
}
```

#### Error Responses
- `404 Not Found`: `{"error": "Candidate 'cand_9f83a1b2' or skill 'Ruby' not found"}`

---

### 2.4 POST `/api/test/{candidate_id}/{skill}/answer`
Submits an answer for the active question. Evaluates the response and returns question evaluation result and completion status.

- **Content-Type**: `application/json`
- **Path Parameters**:
  - `candidate_id` (string): e.g. `"cand_9f83a1b2"`
  - `skill` (string): e.g. `"Python"`
- **Request Body**:
  ```json
  {
    "question_id": "py_q04",
    "answer": "def chunked(iterable, n):\n    chunk = []\n    for item in iterable:\n        chunk.append(item)\n        if len(chunk) == n:\n            yield chunk\n            chunk = []\n    if chunk:\n        yield chunk"
  }
  ```

#### Response (200 OK)
```json
{
  "correct": true,
  "score": 0.95,
  "done": false
}
```

#### Error Responses
- `400 Bad Request`: `{"error": "Missing question_id or answer"}`
- `404 Not Found`: `{"error": "Question 'py_q99' not found for active test session"}`

---

### 2.5 GET `/api/candidates`
Returns the dashboard list of all evaluated candidates with aggregated skill status counts.

#### Response (200 OK)
```json
[
  {
    "candidate_id": "cand_9f83a1b2",
    "name": "Alex Mercer",
    "counts": {
      "confirmed": 2,
      "underclaimed": 1,
      "overclaimed": 0
    }
  },
  {
    "candidate_id": "cand_3c7a9e10",
    "name": "Morgan Vance",
    "counts": {
      "confirmed": 1,
      "underclaimed": 0,
      "overclaimed": 2
    }
  }
]
```

---

### 2.6 GET `/api/candidates/{id}/report`
Returns the comprehensive verification report for a candidate, including evidence scores, test scores, verified levels, status badges, and AI insights.

- **Path Parameter**: `id` (string): e.g. `"cand_9f83a1b2"`

#### Response (200 OK)
```json
{
  "candidate": {
    "id": "cand_9f83a1b2",
    "name": "Alex Mercer",
    "projects": [
      "High-throughput Event Ingestion Engine (Python, Kafka)",
      "PostgreSQL Analytics Warehouse Migration",
      "Churn Prediction Pipeline (scikit-learn)"
    ],
    "certifications": [
      "AWS Certified Solutions Architect",
      "DeepLearning.AI Specialization"
    ]
  },
  "skills": [
    {
      "skill": "Python",
      "claimed_level": "Advanced",
      "evidence_score": 85,
      "test_score": 92,
      "final_score": 89.2,
      "verified_level": "Advanced",
      "status": "confirmed",
      "explanation": "Candidate demonstrated deep mastery of asynchronous programming, generators, and clean architecture matching claimed Advanced level."
    },
    {
      "skill": "SQL",
      "claimed_level": "Intermediate",
      "evidence_score": 75,
      "test_score": 90,
      "final_score": 84.0,
      "verified_level": "Advanced",
      "status": "underclaimed",
      "explanation": "Claimed Intermediate level but successfully executed complex analytic window functions and index optimization corresponding to Advanced level."
    },
    {
      "skill": "Machine Learning",
      "claimed_level": "Intermediate",
      "evidence_score": 42,
      "test_score": 48,
      "final_score": 45.6,
      "verified_level": "Beginner",
      "status": "overclaimed",
      "explanation": "Claimed Intermediate level but struggled with cross-validation methodology, regularization principles, and metric selection."
    }
  ],
  "insights": {
    "hidden": [
      "SQL execution and data modeling performance surpasses candidate self-assessment.",
      "High code readability, docstring conventions, and defensive error handling."
    ],
    "improve": [
      "Deepen understanding of machine learning loss functions and evaluation tradeoffs (Precision vs Recall).",
      "Practice distributed query execution plans and database partitioning schemes."
    ]
  }
}
```

#### Error Responses
- `404 Not Found`: `{"error": "Candidate 'cand_9f83a1b2' not found"}`

---

### 2.7 GET `/api/demo`
Provides a seeded candidate ID for instant zero-friction demonstration during judging or testing.

#### Response (200 OK)
```json
{
  "candidate_id": "cand_demo_001"
}
```

---

### 2.8 POST `/api/reset`
Resets the database to a clean initial state pre-populated with default demo candidate fixtures.

#### Response (200 OK)
```json
{
  "status": "ok"
}
```

---

## 3. Status Classification Reference Matrix

Final Score Calculation: `final_score = 0.4 * evidence_score + 0.6 * test_score`

| Level | Final Score Range |
| :--- | :--- |
| **Beginner** | 0 – 49.9 |
| **Intermediate** | 50 – 74.9 |
| **Advanced** | 75 – 100 |

| Status | Condition | Meaning |
| :--- | :--- | :--- |
| `confirmed` | `verified_level == claimed_level` | Candidate's skill matches their claim |
| `underclaimed` | `verified_level > claimed_level` | Candidate is stronger than they claimed (hidden gem) |
| `overclaimed` | `verified_level < claimed_level` | Candidate claimed higher than verified evidence & test |

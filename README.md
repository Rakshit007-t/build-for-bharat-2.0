# 👻 Ghost Skills

> **AI Skill Verification Layer for Hiring**  
> Verifying claimed candidate abilities through resume evidence, optional GitHub analysis, and adaptive skill tests.

---

## 💡 Overview

Resumes are full of inflated claims and hidden gems. **Ghost Skills** bridges the gap between what candidates claim and what they can actually do:
1. **Resume Ingestion**: Candidate uploads a PDF or text resume.
2. **AI Skill Extraction**: Gemini extracts claimed technical competencies and claimed proficiency levels (`Beginner`, `Intermediate`, `Advanced`).
3. **Evidence Scoring (0–100)**: Resume text snippets and optional GitHub repositories are evaluated for tangible proof.
4. **Adaptive Diagnostic Test (0–100)**: 5 calibrated questions per skill adapt to the candidate's responses.
5. **Final Composite Verification**:
   $$\text{Final Score} = 0.4 \times \text{Evidence Score} + 0.6 \times \text{Test Score}$$
6. **Classification**:
   - **Confirmed**: Verified level matches claimed level.
   - **Underclaimed**: Candidate demonstrated higher mastery than claimed (hidden talent).
   - **Overclaimed**: Verification reveals a gap relative to claimed ability.

**MVP Target Skills**: `Python`, `SQL`, `Machine Learning`.

---

## 👥 Team Ownership & Architecture

| Team Member | Scope | Focus Areas |
| :--- | :--- | :--- |
| **Person A** | `backend/` | FastAPI routes, Gemini prompt engineering, SQLite models, scoring engine |
| **Person B** | `frontend/`, `content/` | Static Tailwind UI, question banks, sample resumes, test runner UI |

- See [API_CONTRACT.md](API_CONTRACT.md) for the frozen endpoint specifications and example payloads.
- See [PLAN.md](PLAN.md) for the 21-hour hackathon execution roadmap and database schema.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11, [FastAPI](https://fastapi.tiangolo.com/), [uvicorn](https://www.uvicorn.org/), [SQLite](https://www.sqlite.org/), [pypdf](https://pypdf.readthedocs.io/), Google Gemini (`google-genai`)
- **Frontend**: Single static HTML + Tailwind CSS (CDN) + Vanilla JavaScript (Zero build step, zero React)
- **Testing**: `pytest`

---

## 🚀 Quickstart

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# Or on macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys
Copy `.env.example` to `.env` and configure your Gemini API key:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run Development Server
```bash
uvicorn backend.main:app --reload --port 8000
```
- Open [http://localhost:8000](http://localhost:8000) for the Ghost Skills application.
- API documentation (Swagger) is available at [http://localhost:8000/docs](http://localhost:8000/docs).
- Health check: [http://localhost:8000/health](http://localhost:8000/health).

---

## 📂 Repository Layout

```
ghost-skills/
├── backend/
│   ├── __init__.py
│   └── main.py          # FastAPI application & route mount
├── frontend/
│   ├── index.html       # Single-page UI with Tailwind CDN
│   └── app.js           # Vanilla JS application
├── content/
│   ├── questions/       # Curated question banks (Python, SQL, ML)
│   └── samples/         # Demo resumes & test payloads
├── API_CONTRACT.md      # Exact REST API request/response specifications
├── PLAN.md              # 21-hour execution timeline & SQLite schema
├── requirements.txt     # Python dependencies
├── .env.example         # Template environment variables
├── .gitignore           # Git ignore rules
└── README.md            # Project overview & instructions
```

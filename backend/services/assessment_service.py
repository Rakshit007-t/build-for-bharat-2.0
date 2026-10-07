"""Local SQLite persistence and adaptive assessment orchestration."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.services.verification_service import build_result


class AssessmentService:
    def __init__(self, database_path: Path | None = None, question_root: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        self.database_path = database_path or root / "data" / "local" / "verification.sqlite3"
        self.question_root = question_root or root / "content" / "questions"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id TEXT PRIMARY KEY, name TEXT NOT NULL, education TEXT,
                    resume_text TEXT NOT NULL, projects_json TEXT NOT NULL, certifications_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS skill_claims (
                    candidate_id TEXT NOT NULL, skill TEXT NOT NULL, slug TEXT NOT NULL, claimed_level TEXT NOT NULL,
                    snippets_json TEXT NOT NULL, details_json TEXT NOT NULL, PRIMARY KEY(candidate_id, skill),
                    FOREIGN KEY(candidate_id) REFERENCES candidates(candidate_id)
                );
                CREATE TABLE IF NOT EXISTS test_sessions (
                    session_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, skill TEXT NOT NULL,
                    answered_count INTEGER NOT NULL DEFAULT 0, next_difficulty TEXT NOT NULL DEFAULT 'medium',
                    current_question_id TEXT, correct_weight REAL NOT NULL DEFAULT 0, total_weight REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active', test_score REAL, created_at TEXT NOT NULL, completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS assessment_answers (
                    session_id TEXT NOT NULL, question_index INTEGER NOT NULL, question_id TEXT NOT NULL,
                    difficulty TEXT NOT NULL, selected_answer TEXT NOT NULL, correct INTEGER NOT NULL,
                    weight INTEGER NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(session_id, question_index)
                );
                CREATE TABLE IF NOT EXISTS candidate_skill_results (
                    candidate_id TEXT NOT NULL, skill TEXT NOT NULL, session_id TEXT NOT NULL,
                    result_json TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(candidate_id, skill)
                );
            """)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_candidate(self, extracted: dict[str, Any], resume_text: str) -> str:
        candidate_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?)", (
                candidate_id, extracted["name"], extracted.get("education"), resume_text,
                json.dumps(extracted.get("projects", [])), json.dumps(extracted.get("certifications", [])), self._now()))
            for claim in extracted["skills"]:
                db.execute("INSERT INTO skill_claims VALUES (?, ?, ?, ?, ?, ?)", (
                    candidate_id, claim["skill"], claim["slug"], claim["claimed_level"],
                    json.dumps(claim["evidence_snippets"]), json.dumps(claim["evidence_details"])))
        return candidate_id

    def candidate(self, candidate_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
            if row is None:
                return None
            claims = db.execute("SELECT * FROM skill_claims WHERE candidate_id=? ORDER BY CASE skill WHEN 'Python' THEN 1 WHEN 'SQL' THEN 2 ELSE 3 END", (candidate_id,)).fetchall()
        return {"candidate_id": row["candidate_id"], "name": row["name"], "education": row["education"],
                "projects": json.loads(row["projects_json"]), "certifications": json.loads(row["certifications_json"]),
                "created_at": row["created_at"], "skills": [{"skill": claim["skill"], "slug": claim["slug"],
                "claimed_level": claim["claimed_level"], "evidence_snippets": json.loads(claim["snippets_json"]),
                "evidence_details": json.loads(claim["details_json"])} for claim in claims]}

    def _question_bank(self, slug: str) -> list[dict[str, Any]]:
        path = self.question_root / f"{slug}.json"
        try:
            bank = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Question bank {slug} is unavailable or invalid.") from exc
        if not isinstance(bank, list) or len(bank) < 6:
            raise RuntimeError(f"Question bank {slug} must contain at least six questions.")
        return bank

    def start(self, candidate_id: str, skill: str) -> str:
        candidate = self.candidate(candidate_id)
        if candidate is None:
            raise KeyError("Candidate not found.")
        claim = next((item for item in candidate["skills"] if item["skill"].casefold() == skill.casefold()), None)
        if claim is None:
            raise ValueError("Select a skill detected in this resume.")
        self._question_bank(claim["slug"])
        session_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("INSERT INTO test_sessions(session_id,candidate_id,skill,created_at) VALUES(?,?,?,?)",
                       (session_id, candidate_id, claim["skill"], self._now()))
        return session_id

    def next_question(self, candidate_id: str) -> dict[str, Any]:
        with self._connect() as db:
            session = db.execute("SELECT * FROM test_sessions WHERE candidate_id=? AND status='active' ORDER BY created_at DESC LIMIT 1", (candidate_id,)).fetchone()
            if session is None:
                raise KeyError("No active assessment. Start verification first.")
            if session["answered_count"] >= 3:
                return {"done": True}
            candidate = db.execute("SELECT slug FROM skill_claims WHERE candidate_id=? AND skill=?", (candidate_id, session["skill"])).fetchone()
            bank = self._question_bank(candidate["slug"])
            asked = {row[0] for row in db.execute("SELECT question_id FROM assessment_answers WHERE session_id=?", (session["session_id"],))}
            if session["current_question_id"]:
                question_id = session["current_question_id"]
                question = next(item for item in bank if item["id"] == question_id)
            else:
                available = [item for item in bank if item["difficulty"] == session["next_difficulty"] and item["id"] not in asked]
                if not available:
                    raise RuntimeError(f"No unused {session['next_difficulty']} question remains.")
                question = available[session["answered_count"] % len(available)]
                db.execute("UPDATE test_sessions SET current_question_id=? WHERE session_id=?", (question["id"], session["session_id"]))
            return {"question_id": question["id"], "skill": session["skill"], "type": "mcq", "prompt": question["prompt"],
                    "options": question["options"], "difficulty": question["difficulty"], "index": session["answered_count"] + 1,
                    "total": 3, "done": False}

    def answer(self, candidate_id: str, question_id: str, answer: str) -> dict[str, Any]:
        with self._connect() as db:
            session = db.execute("SELECT * FROM test_sessions WHERE candidate_id=? AND status='active' ORDER BY created_at DESC LIMIT 1", (candidate_id,)).fetchone()
            if session is None or not session["current_question_id"] or session["current_question_id"] != question_id:
                raise ValueError("Question does not match the active assessment step.")
            claim = db.execute("SELECT * FROM skill_claims WHERE candidate_id=? AND skill=?", (candidate_id, session["skill"])).fetchone()
            bank = self._question_bank(claim["slug"])
            question = next(item for item in bank if item["id"] == question_id)
            options = question["options"]
            selected_index = next((i for i, option in enumerate(options) if option.casefold() == answer.casefold()), None)
            if selected_index is None and answer.isdigit() and 0 <= int(answer) < len(options):
                selected_index = int(answer)
            if selected_index is None:
                raise ValueError("Answer must match one of the displayed options.")
            correct = selected_index == question["answer_index"]
            weight = {"easy": 1, "medium": 2, "hard": 3}[question["difficulty"]]
            right_weight = session["correct_weight"] + (weight if correct else 0)
            total_weight = session["total_weight"] + weight
            count = session["answered_count"] + 1
            raw_score = round(right_weight / total_weight, 4)
            db.execute("INSERT INTO assessment_answers VALUES(?,?,?,?,?,?,?,?)", (session["session_id"], count, question_id,
                       question["difficulty"], options[selected_index], int(correct), weight, self._now()))
            done = count == 3
            next_diff = {"easy": "medium", "medium": "hard", "hard": "hard"}.get(question["difficulty"]) if correct else {"easy": "easy", "medium": "easy", "hard": "medium"}[question["difficulty"]]
            test_score = raw_score * 100
            db.execute("UPDATE test_sessions SET answered_count=?, next_difficulty=?, current_question_id=NULL, correct_weight=?, total_weight=?, status=?, test_score=?, completed_at=? WHERE session_id=?",
                       (count, next_diff, right_weight, total_weight, "complete" if done else "active", test_score if done else None, self._now() if done else None, session["session_id"]))
            if done:
                full_claim = {"skill": claim["skill"], "claimed_level": claim["claimed_level"],
                              "evidence_details": json.loads(claim["details_json"]), "evidence_snippets": json.loads(claim["snippets_json"])}
                result = build_result(full_claim, test_score)
                db.execute("INSERT OR REPLACE INTO candidate_skill_results VALUES(?,?,?,?,?)", (candidate_id, claim["skill"], session["session_id"], json.dumps(result), self._now()))
            return {"correct": correct, "score": raw_score, "difficulty": question["difficulty"],
                    "explanation": question["explanation"], "done": done, "test_score": round(test_score, 1) if done else None}

    def report(self, candidate_id: str) -> dict[str, Any] | None:
        candidate = self.candidate(candidate_id)
        if candidate is None:
            return None
        with self._connect() as db:
            rows = db.execute("SELECT skill,result_json FROM candidate_skill_results WHERE candidate_id=?", (candidate_id,)).fetchall()
        results = {row["skill"]: json.loads(row["result_json"]) for row in rows}
        skills = []
        for claim in candidate["skills"]:
            result = results.get(claim["skill"])
            if result is None:
                result = {"skill": claim["skill"], "claimed_level": claim["claimed_level"], "evidence_score": None,
                          "test_score": None, "final_score": None, "verified_level": None,
                          "status": "pending" if claim["claimed_level"] != "Unspecified" else "unverified",
                          "evidence_snippets": claim["evidence_snippets"], "evidence_details": claim["evidence_details"],
                          "explanation": "Complete the local assessment to calculate a verification result."}
            skills.append(result)
        return {"candidate": {key: candidate[key] for key in ("candidate_id", "name", "education", "created_at")}, "skills": skills,
                "projects": candidate["projects"], "certifications": candidate["certifications"],
                "notice": "Prototype heuristic evidence score. Local assessment. Not a hiring decision."}

    def stats(self) -> dict[str, int]:
        counts = {"confirmed": 0, "underclaimed": 0, "overclaimed": 0}
        with self._connect() as db:
            rows = db.execute("SELECT result_json FROM candidate_skill_results").fetchall()
        for row in rows:
            status = json.loads(row["result_json"]).get("status")
            if status in counts:
                counts[status] += 1
        return counts

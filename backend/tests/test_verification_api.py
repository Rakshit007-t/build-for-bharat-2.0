import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.assessment_service import AssessmentService


@pytest.fixture
def client(tmp_path):
    app.state.assessment_service = AssessmentService(tmp_path / "verification.sqlite3")
    with TestClient(app) as test_client:
        yield test_client


def upload_sample(client, sample="overclaimed_resume.txt"):
    text = open(f"content/samples/{sample}", encoding="utf-8").read()
    response = client.post("/api/verification/upload", data={"text": text})
    assert response.status_code == 200, response.text
    return response.json()


def test_upload_api_extracts_claims_without_returning_raw_resume(client):
    uploaded = upload_sample(client)
    assert uploaded["name"] == "Aanya Mehta"
    assert [(row["skill"], row["claimed_level"]) for row in uploaded["skills"]] == [
        ("Python", "Advanced"), ("SQL", "Advanced"), ("Machine Learning", "Advanced")]
    candidate = client.get(f"/api/verification/{uploaded['candidate_id']}").json()
    assert "resume_text" not in candidate
    assert candidate["name"] == uploaded["name"]


def test_txt_file_upload_and_validation(client):
    text = "Name: Local Candidate\nPython — Familiar\n"
    good = client.post("/api/verification/upload", files={"file": ("resume.txt", text, "text/plain")})
    bad = client.post("/api/verification/upload", files={"file": ("resume.docx", text, "application/octet-stream")})
    assert good.status_code == 200
    assert good.json()["skills"][0]["claimed_level"] == "Beginner"
    assert bad.status_code == 415


def test_question_answer_adaptation_and_report_api(client):
    uploaded = upload_sample(client)
    candidate_id = uploaded["candidate_id"]
    start = client.post(f"/api/verification/{candidate_id}/start", json={"skill": "Python"})
    assert start.status_code == 200
    first = client.get(f"/api/verification/{candidate_id}/next").json()
    assert first["difficulty"] == "medium" and first["index"] == 1
    assert "answer_index" not in first
    assert client.get(f"/api/verification/{candidate_id}/next").json()["question_id"] == first["question_id"]
    bank = json.load(open("content/questions/python.json", encoding="utf-8"))
    question = next(row for row in bank if row["id"] == first["question_id"])
    # Deliberately miss all three for the main overclaim demo path.
    wrong = question["options"][(question["answer_index"] + 1) % 4]
    answer = client.post(f"/api/verification/{candidate_id}/answer", json={"question_id": first["question_id"], "answer": wrong}).json()
    assert answer["correct"] is False and answer["score"] == 0
    second = client.get(f"/api/verification/{candidate_id}/next").json()
    assert second["difficulty"] == "easy" and second["index"] == 2
    for current in [second]:
        q = next(row for row in bank if row["id"] == current["question_id"])
        choice = q["options"][(q["answer_index"] + 1) % 4]
        result = client.post(f"/api/verification/{candidate_id}/answer", json={"question_id": current["question_id"], "answer": choice}).json()
    third = client.get(f"/api/verification/{candidate_id}/next").json()
    q = next(row for row in bank if row["id"] == third["question_id"])
    choice = q["options"][(q["answer_index"] + 1) % 4]
    result = client.post(f"/api/verification/{candidate_id}/answer", json={"question_id": third["question_id"], "answer": choice}).json()
    assert result["done"] is True and result["test_score"] == 0
    report = client.get(f"/api/verification/{candidate_id}/report").json()
    python = next(row for row in report["skills"] if row["skill"] == "Python")
    assert python["status"] == "overclaimed"
    assert python["verified_level"] == "Beginner"
    assert python["final_score"] == 0
    assert client.get("/api/verification/stats").json()["overclaimed"] == 1


def test_unspecified_level_stays_unverified_after_test(client):
    uploaded = client.post("/api/verification/upload", data={"text": "Name: No Level\nPython project experience"}).json()
    assert uploaded["skills"][0]["claimed_level"] == "Unspecified"
    candidate_id = uploaded["candidate_id"]
    client.post(f"/api/verification/{candidate_id}/start", json={"skill": "Python"})
    bank = json.load(open("content/questions/python.json", encoding="utf-8"))
    for index in range(3):
        question = client.get(f"/api/verification/{candidate_id}/next").json()
        item = next(row for row in bank if row["id"] == question["question_id"])
        client.post(f"/api/verification/{candidate_id}/answer", json={"question_id": question["question_id"], "answer": item["options"][item["answer_index"]]})
    result = client.get(f"/api/verification/{candidate_id}/report").json()["skills"][0]
    assert result["status"] == "unverified"
    assert result["verified_level"] is None


def complete_python_test(client, candidate_id, outcomes):
    bank = json.load(open("content/questions/python.json", encoding="utf-8"))
    client.post(f"/api/verification/{candidate_id}/start", json={"skill": "Python"})
    for correct in outcomes:
        question = client.get(f"/api/verification/{candidate_id}/next").json()
        item = next(row for row in bank if row["id"] == question["question_id"])
        index = item["answer_index"] if correct else (item["answer_index"] + 1) % 4
        response = client.post(f"/api/verification/{candidate_id}/answer", json={"question_id": question["question_id"], "answer": item["options"][index]})
        assert response.status_code == 200, response.text
    return next(row for row in client.get(f"/api/verification/{candidate_id}/report").json()["skills"] if row["skill"] == "Python")


def test_confirmed_and_underclaimed_synthetic_flows_are_score_derived(client):
    confirmed = upload_sample(client, "confirmed_resume.txt")
    # Medium correct, hard correct, then one hard miss -> weighted 62.5% test.
    confirmed_python = complete_python_test(client, confirmed["candidate_id"], [True, True, False])
    assert confirmed_python["evidence_score"] == 60
    assert confirmed_python["test_score"] == 62.5
    assert confirmed_python["final_score"] == 61.5
    assert confirmed_python["status"] == "confirmed"

    underclaimed = upload_sample(client, "underclaimed_resume.txt")
    underclaimed_python = complete_python_test(client, underclaimed["candidate_id"], [True, True, True])
    assert underclaimed_python["evidence_score"] == 52.5
    assert underclaimed_python["test_score"] == 100
    assert underclaimed_python["status"] == "underclaimed"
    assert underclaimed_python["verified_level"] == "Advanced"

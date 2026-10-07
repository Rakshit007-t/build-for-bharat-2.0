# Verification API

All routes are local FastAPI endpoints. Resume text and SQLite records remain on the running machine. The API never returns the full persisted resume text or a question's `answer_index`.

## Upload a PDF/TXT file or text

`POST /api/verification/upload` accepts multipart form data with either `file` or `text`.

```bash
curl -F "file=@resume.pdf" http://127.0.0.1:8000/api/verification/upload
curl -F "text=Name: Demo Candidate%0APython — Intermediate" http://127.0.0.1:8000/api/verification/upload
```

The response contains `candidate_id`, `name`, optional `education`, detected `skills` with `claimed_level` and literal `evidence_snippets`, plus extracted project/certification bullets. Uploads over 5 MB, empty/scanned-only PDFs, unsupported file types, or resumes without a supported skill return an explanatory 4xx response.

## Read candidate claims

`GET /api/verification/{candidate_id}` returns candidate metadata, claims, evidence snippets, and extraction summaries. It omits the raw resume text.

## Start and answer an assessment

`POST /api/verification/{candidate_id}/start`

```json
{"skill":"Python"}
```

Returns a local `session_id`. `GET /api/verification/{candidate_id}/next` returns a sanitized MCQ with four options, difficulty, 1-based index, and total. The answer key is not included.

`POST /api/verification/{candidate_id}/answer`

```json
{"question_id":"py-m1","answer":"[0, 2, 4]"}
```

Returns correctness, the cumulative weighted score in `[0,1]`, difficulty, an explanation, and whether the three-question assessment is complete. The final answer also includes the test percentage. Repeating `next` before answering returns the same question.

## Report and local counts

- `GET /api/verification/{candidate_id}/report` returns completed skill results and leaves untested skills pending.
- `GET /api/verification/stats` returns local counts for confirmed, underclaimed, and overclaimed skill results.
- `GET /api/verification/demo/{overclaimed_resume.txt|underclaimed_resume.txt|confirmed_resume.txt}` reads one allow-listed bundled synthetic demo resume for the UI.

## Error behavior

Unknown candidates return 404; starting a skill not detected in the resume returns 422; asking for the next question without an active assessment returns 409; invalid file types return 415; malformed/non-readable resumes return 422. The normal JDS/SDS model and job-market endpoints are independent of these routes.

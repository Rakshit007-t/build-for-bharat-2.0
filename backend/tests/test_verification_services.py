import json
from pathlib import Path

from backend.services.resume_service import extract_pdf_text, parse_resume
from backend.services.verification_service import classify, final_score, score_evidence, verified_level


ROOT = Path(__file__).resolve().parents[2]


def test_txt_skill_level_and_evidence_extraction():
    parsed = parse_resume("""Name: Demo Person
Python — Advanced
SQL — working knowledge
Machine Learning
Projects
- Built a Python tool and analyzed sample data.
""")
    claims = {row["skill"]: row for row in parsed["skills"]}
    assert claims["Python"]["claimed_level"] == "Advanced"
    assert claims["SQL"]["claimed_level"] == "Intermediate"
    assert claims["Machine Learning"]["claimed_level"] == "Unspecified"
    assert claims["Python"]["evidence_snippets"] == ["- Built a Python tool and analyzed sample data."]
    assert parsed["projects"] == ["- Built a Python tool and analyzed sample data."]


def test_skill_aliases_and_level_aliases():
    parsed = parse_resume("pandas; numpy; PostgreSQL; scikit-learn in a machine-learning project; basic Python, expert SQL")
    claims = {row["skill"]: row for row in parsed["skills"]}
    assert set(claims) == {"Python", "SQL", "Machine Learning"}
    assert claims["Python"]["claimed_level"] == "Beginner"
    assert claims["SQL"]["claimed_level"] == "Advanced"


def test_pdf_text_extraction_with_pypdf(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 72 720 Td (Python Advanced) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    pdf_path = tmp_path / "resume.pdf"
    with pdf_path.open("wb") as file:
        writer.write(file)
    assert "Python Advanced" in extract_pdf_text(pdf_path.read_bytes())


def test_evidence_score_is_category_capped_and_repeatable():
    details = ["Project evidence identified in a relevant resume excerpt (+20 per item, up to 40)."] * 3
    result = score_evidence(details, ["Built Python project", "Created Python project", "Developed Python project"])
    assert result["score"] == 40
    assert score_evidence(details, ["Built Python project"])["score"] == 40


def test_score_bands_and_all_claim_comparison_outcomes():
    assert final_score(25, 33.3) == 30.0
    assert verified_level(39.9) == "Beginner"
    assert verified_level(40) == "Intermediate"
    assert verified_level(70) == "Intermediate"
    assert verified_level(70.1) == "Advanced"
    assert classify("Intermediate", "Intermediate") == "confirmed"
    assert classify("Intermediate", "Advanced") == "underclaimed"
    assert classify("Advanced", "Beginner") == "overclaimed"
    assert classify("Unspecified", "Advanced") == "unverified"


def test_sample_resumes_are_synthetic_and_have_intended_claims():
    overclaimed = parse_resume((ROOT / "content/samples/overclaimed_resume.txt").read_text(encoding="utf-8"))
    assert [(item["skill"], item["claimed_level"]) for item in overclaimed["skills"]] == [
        ("Python", "Advanced"), ("SQL", "Advanced"), ("Machine Learning", "Advanced")]
    assert all("SYNTHETIC DEMO" in (ROOT / "content/samples" / name).read_text(encoding="utf-8")
               for name in ["overclaimed_resume.txt", "underclaimed_resume.txt", "confirmed_resume.txt"])


def test_question_banks_have_two_questions_per_difficulty_and_private_answer_key():
    for slug in ("python", "sql", "ml"):
        bank = json.loads((ROOT / "content/questions" / f"{slug}.json").read_text(encoding="utf-8"))
        assert len(bank) == 6
        assert {difficulty: sum(row["difficulty"] == difficulty for row in bank) for difficulty in ("easy", "medium", "hard")} == {"easy": 2, "medium": 2, "hard": 2}
        assert all(len(row["options"]) == 4 and 0 <= row["answer_index"] < 4 for row in bank)

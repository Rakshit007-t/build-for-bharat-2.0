from pathlib import Path

import pandas as pd
import pytest

from model.src.cleaning import clean_frame, parse_experience, parse_salary
from model.src.io import load_dataset, standardize_column_name


@pytest.mark.parametrize("filename", ["Analytics Jobs.csv", "DataScience Jobs.csv", "JDS Skill Traits.xlsx", "SDS Personality Traits.xlsx"])
def test_organizer_dataset_loads_when_present(filename):
    path = Path("data/raw") / filename
    if not path.is_file():
        pytest.skip(f"Organizer-provided input is not present: {path}")
    frame = load_dataset(path)
    assert len(frame.columns) > 0


def test_column_names_preserve_words_with_standard_separators():
    assert standardize_column_name("Maths-Stats Skills") == "maths_stats_skills"
    assert standardize_column_name("success_ classification_ high_low") == "success_classification_high_low"


def test_salary_and_experience_parsing_are_conservative():
    assert parse_salary("₹6-8 LPA") == 7
    assert parse_salary("$40/hour") is None
    assert parse_experience("2-4 years") == 3
    assert parse_experience("Fresher") == 0


def test_cleaning_audit_records_removed_duplicates_and_keeps_original_fields():
    original = pd.DataFrame({
        "Job Title": [" Analyst  ", " Analyst  "],
        "Salary Estimate": ["6-8 LPA", "6-8 LPA"],
        "Experience": ["2-4 years", "2-4 years"],
        "Skills": ["Python, SQL", "Python, SQL"],
    })
    cleaned, report = clean_frame(original, "test_fixture")
    assert len(cleaned) == 1
    assert report["duplicate_rows_removed"] == 1
    assert report["duplicate_indices_removed"] == ["1"]
    assert "salary_estimate" in cleaned.columns
    assert "salary_estimate_numeric" in cleaned.columns
    assert "experience_years_numeric" in cleaned.columns
    assert "skills_normalized" in cleaned.columns


def test_csv_loader_standardizes_without_mutating_source(tmp_path):
    path = tmp_path / "small.csv"
    path.write_text("Maths-Stats Skills,Role\n3,Analyst\n", encoding="utf-8")
    before = path.read_bytes()
    frame = load_dataset(path)
    assert list(frame.columns) == ["maths_stats_skills", "role"]
    assert path.read_bytes() == before

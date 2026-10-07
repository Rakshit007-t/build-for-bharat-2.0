import re
from typing import Any

import pandas as pd

from model.src.io import standardize_columns


MISSING_TEXT = {"", "na", "n/a", "n.a.", "null", "none", "-", "--", "unknown", "not available"}


def normalize_text(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text.lower() in MISSING_TEXT:
        return pd.NA
    return text


def parse_salary(value: Any) -> float | None:
    """Parse an explicit salary range/value conservatively; leave ambiguous bands missing."""
    if pd.isna(value):
        return None
    text = str(value).lower().replace(",", "").replace("₹", "").replace("$", "")
    if any(token in text for token in ("hour", "/hr", "hourly")):
        return None
    if any(token in text for token in ("month", "/mo", "monthly")):
        multiplier = 12
    elif any(token in text for token in ("lpa", "lakh", "lac")) or re.search(r"\d(?:\.\d+)?\s*l$", text):
        # Preserve the dataset's lakh scale; do not convert or imply a time period.
        multiplier = 1
    else:
        # A band such as "6to10" does not encode its salary unit, so keep it categorical.
        if not any(token in text for token in ("year", "annual", "annum", "per annum", "k", "₹", "$", "€")):
            return None
        multiplier = 1
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    if not nums:
        return None
    if "lpa" in text or "lakh" in text or "lac" in text or re.search(r"\d(?:\.\d+)?\s*l$", text):
        pass
    elif "k" in text:
        nums = [n * 1000 for n in nums]
    elif "million" in text:
        nums = [n * 1000000 for n in nums]
    return sum(nums) / len(nums) * multiplier


def parse_experience(value: Any) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).lower().strip()
    if any(word in text for word in ("fresher", "entry level", "entry-level", "no experience")):
        return 0.0
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    if not nums:
        return None
    if "month" in text and "year" not in text:
        nums = [n / 12 for n in nums]
    return sum(nums) / len(nums)


def normalize_skill_text(value: Any) -> list[str]:
    text = normalize_text(value)
    if pd.isna(text):
        return []
    parts = re.split(r"[,;|\n]+", str(text))
    normalized = []
    for part in parts:
        cleaned = re.sub(r"\.{2,}$", "", part).strip(" .\t").lower()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if cleaned and cleaned not in {"na", "n/a", "none", "unknown"}:
            normalized.append(cleaned)
    return normalized


def clean_frame(frame: pd.DataFrame, dataset_name: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean conservatively and return a full transformation log."""
    result = standardize_columns(frame)
    report: dict[str, Any] = {
        "dataset": dataset_name,
        "input_rows": int(len(result)),
        "input_columns": int(len(result.columns)),
        "column_standardization": "lowercase words, underscore separators, punctuation removed",
        "text_cells_normalized": 0,
        "duplicate_rows_found": int(result.duplicated().sum()),
        "duplicate_rows_removed": 0,
        "duplicate_indices_removed": [],
        "missing_tokens_normalized": sorted(MISSING_TEXT),
        "salary_columns_parsed": {},
        "experience_columns_parsed": {},
        "skill_columns_normalized": [],
        "notes": [],
    }

    for col in result.select_dtypes(include=["object", "string"]).columns:
        before = result[col].copy()
        result[col] = result[col].map(normalize_text)
        report["text_cells_normalized"] += int((before.fillna("<NA>") != result[col].fillna("<NA>")).sum())

    for col in result.columns:
        if "salary" in col or "compensation" in col:
            parsed = result[col].map(parse_salary)
            if parsed.notna().any():
                result[f"{col}_numeric"] = parsed
                report["salary_columns_parsed"][col] = {
                    "output_column": f"{col}_numeric",
                    "unit": "source scale; monthly values annualized where marked; lakh notation retained in lakh units; ambiguous bands remain missing; period not inferred",
                    "parsed_values": int(parsed.notna().sum()),
                }
        is_experience_field = (
            col in {"experience", "min_experience", "max_experience", "years_of_experience", "experience_required", "required_experience"}
            or col.startswith("experience_")
        )
        if is_experience_field:
            parsed = result[col].map(parse_experience)
            if parsed.notna().any():
                result[f"{col}_years_numeric"] = parsed
                report["experience_columns_parsed"][col] = {
                    "output_column": f"{col}_years_numeric",
                    "unit": "years; ranges represented by midpoint",
                    "parsed_values": int(parsed.notna().sum()),
                }
        if ("skill" in col or "technology" in col) and pd.api.types.is_string_dtype(result[col].dtype):
            result[f"{col}_normalized"] = result[col].map(normalize_skill_text)
            report["skill_columns_normalized"].append(col)

    comparable = result.apply(lambda column: column.map(lambda value: tuple(value) if isinstance(value, list) else tuple(sorted(value.items())) if isinstance(value, dict) else value))
    duplicated = comparable.duplicated(keep="first")
    report["duplicate_indices_removed"] = [str(index) for index in result.index[duplicated].tolist()]
    report["duplicate_rows_removed"] = int(duplicated.sum())
    result = result.loc[~duplicated].copy()
    report["output_rows"] = int(len(result))
    report["output_columns"] = int(len(result.columns))
    report["rows_dropped_total"] = int(report["input_rows"] - report["output_rows"])
    if report["duplicate_rows_removed"]:
        report["notes"].append("Exact duplicate rows removed; original row indices are recorded above.")
    return result, report

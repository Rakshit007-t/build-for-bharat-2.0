import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


def standardize_column_name(value: Any) -> str:
    """Make column labels consistent while retaining their words and meaning."""
    text = str(value).strip().lower()
    text = text.replace("&", " and ").replace("%", " percent ")
    text = re.sub(r"[\s\-/\\]+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unnamed"


def standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy(deep=True)
    names: list[str] = []
    counts: dict[str, int] = {}
    for original in result.columns:
        base = standardize_column_name(original)
        counts[base] = counts.get(base, 0) + 1
        names.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
    result.columns = names
    return result


def load_dataset(path: str | Path) -> pd.DataFrame:
    """Load a local CSV/XLSX file without modifying its source bytes."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Dataset not found: {source}")
    suffix = source.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(source, low_memory=False)
    elif suffix in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(source, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported dataset format: {suffix}")
    return standardize_columns(frame)


def audit_frame(frame: pd.DataFrame, dataset_name: str) -> dict[str, Any]:
    return {
        "dataset": dataset_name,
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "column_names": [str(col) for col in frame.columns],
        "duplicate_rows": int(frame.duplicated().sum()),
        "missing_values_by_column": {str(key): int(value) for key, value in frame.isna().sum().items()},
        "missing_cells": int(frame.isna().sum().sum()),
    }


def write_json(payload: Any, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from model.src.cleaning import clean_frame, normalize_skill_text


ROLE_TERMS = ("job_title", "job_desig", "designation", "title", "role", "position")
LOCATION_TERMS = ("location", "city", "state", "country", "region")
COMPANY_TERMS = ("company", "employer", "organization")
SKILL_TERMS = ("skill", "technology", "tech_stack", "requirement", "qualifications")


def _column(columns: list[str], terms: tuple[str, ...]) -> str | None:
    matches = [(priority, name) for name in columns for priority, term in enumerate(terms) if term in name]
    return min(matches, key=lambda item: (item[0], len(item[1]), item[1]))[1] if matches else None


def _top_values(series: pd.Series | None, limit: int = 10) -> list[dict[str, Any]]:
    if series is None:
        return []
    counts = series.dropna().astype(str).str.strip().replace("", pd.NA).value_counts().head(limit)
    return [{"name": str(name), "count": int(count)} for name, count in counts.items()]


def _location_counts(series: pd.Series | None) -> Counter:
    counts: Counter = Counter()
    if series is None:
        return counts
    for value in series.dropna().astype(str):
        parts = [part.strip() for part in __import__("re").split(r"[,;|]+", value) if part.strip()]
        counts.update(parts)
    return counts


def _skill_counts(frame: pd.DataFrame) -> Counter:
    counts: Counter = Counter()
    for column in frame.columns:
        if column.endswith("_normalized"):
            continue
        if any(term in column for term in SKILL_TERMS):
            for value in frame[column].dropna():
                if isinstance(value, list):
                    counts.update(skill for skill in value if skill)
                else:
                    text = str(value).lower()
                    parts = normalize_skill_text(text)
                    counts.update(parts)
    return counts


def _salary_series(frame: pd.DataFrame) -> pd.Series:
    columns = [col for col in frame.columns if col.endswith("_numeric") and ("salary" in col or "compensation" in col)]
    if not columns:
        return pd.Series(dtype=float)
    return pd.concat([pd.to_numeric(frame[col], errors="coerce") for col in columns], axis=1).bfill(axis=1).iloc[:, 0]


def analyze_job_sources(datasets: dict[str, pd.DataFrame], report_dir: Path, figure_dir: Path) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}
    transforms: list[dict[str, Any]] = []
    combined: list[pd.DataFrame] = []
    processed_dir = report_dir.parent / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    combined_skills = Counter()
    combined_skill_pairs = Counter()
    role_counter = Counter()
    location_counter = Counter()
    company_counter = Counter()

    for name, original in datasets.items():
        frame, clean_report = clean_frame(original, name)
        frame.to_csv(processed_dir / f"{name}_cleaned.csv", index=False)
        frame["source_dataset"] = name
        transforms.append(clean_report)
        roles_col = _column(list(frame.columns), ROLE_TERMS)
        location_col = _column(list(frame.columns), LOCATION_TERMS)
        company_col = _column(list(frame.columns), COMPANY_TERMS)
        jobs_count_col = "num_of_jobs" if "num_of_jobs" in frame.columns else None
        experience_cols = [col for col in frame.columns if col.endswith("_years_numeric")]
        salary_col = _column(list(frame.columns), ("salary", "compensation"))
        salaries = _salary_series(frame)
        skill_counts = _skill_counts(frame)
        combined_skills.update(skill_counts)
        skill_columns = [col for col in frame.columns if any(term in col for term in SKILL_TERMS) and not col.endswith("_normalized")]
        for row_values in frame[skill_columns].itertuples(index=False, name=None) if skill_columns else []:
            row_skills = set()
            for value in row_values:
                if pd.isna(value):
                    continue
                row_skills.update(normalize_skill_text(value))
            combined_skill_pairs.update(combinations(sorted(row_skills), 2))
        weights = pd.to_numeric(frame[jobs_count_col], errors="coerce").fillna(0) if jobs_count_col else pd.Series(1, index=frame.index)
        if roles_col:
            role_counter.update(frame[roles_col].dropna().astype(str).str.strip().value_counts().to_dict())
        if location_col:
            location_counter.update(_location_counts(frame[location_col]))
        if company_col:
            grouped = pd.DataFrame({"name": frame[company_col].astype("string").str.strip(), "weight": weights}).dropna(subset=["name"]).groupby("name")["weight"].sum()
            company_counter.update(grouped.to_dict())
        weighted_role_counts = (
            pd.DataFrame({"name": frame[roles_col].astype("string").str.strip(), "weight": weights})
            .dropna(subset=["name"]).groupby("name")["weight"].sum()
            if roles_col else pd.Series(dtype=float)
        )
        weighted_company_counts = (
            pd.DataFrame({"name": frame[company_col].astype("string").str.strip(), "weight": weights})
            .dropna(subset=["name"]).groupby("name")["weight"].sum()
            if company_col else pd.Series(dtype=float)
        )
        salary_unit = "source scale as labeled in each record; period is not inferred"
        if salary_col and frame[salary_col].dropna().astype(str).str.lower().str.endswith("l").all():
            salary_unit = "lakh units encoded by the source L suffix; salary period is not specified in the field"
        results[name] = {
            "rows": int(len(frame)),
            "reported_job_count_total": int(weights.sum()),
            "reported_job_count_column": jobs_count_col,
            "columns": int(original.shape[1]),
            "role_column_used": roles_col,
            "company_column_used": company_col,
            "location_column_used": location_col,
            "top_roles": _top_values(frame[roles_col] if roles_col else None),
            "top_companies": _top_values(frame[company_col] if company_col else None),
            "top_roles_by_reported_jobs": [{"name": str(key), "count": int(value)} for key, value in weighted_role_counts.sort_values(ascending=False).head(12).items()],
            "top_companies_by_reported_jobs": [{"name": str(key), "count": int(value)} for key, value in weighted_company_counts.sort_values(ascending=False).head(12).items()],
            "top_locations": [{"name": name, "count": int(count)} for name, count in _location_counts(frame[location_col] if location_col else None).most_common(12)],
            "top_skills": [{"name": skill, "count": int(count)} for skill, count in skill_counts.most_common(15)],
            "salary_summary": {
                "unit": salary_unit,
                "category_counts": _top_values(frame[salary_col] if salary_col else None, limit=12),
                "observed_count": int(salaries.notna().sum()),
                "mean": float(salaries.mean()) if salaries.notna().any() else None,
                "median": float(salaries.median()) if salaries.notna().any() else None,
                "min": float(salaries.min()) if salaries.notna().any() else None,
                "max": float(salaries.max()) if salaries.notna().any() else None,
            },
            "experience_summary": {
                "unit": "years",
                "observed_count": int(frame[experience_cols].notna().any(axis=1).sum()) if experience_cols else 0,
                "mean": float(frame[experience_cols].stack().mean()) if experience_cols and frame[experience_cols].notna().any().any() else None,
                "median": float(frame[experience_cols].stack().median()) if experience_cols and frame[experience_cols].notna().any().any() else None,
            },
            "salary_vs_experience_correlation": None,
        }
        if experience_cols and salaries.notna().sum() >= 3:
            experience = frame[experience_cols].bfill(axis=1).iloc[:, 0]
            pair = pd.DataFrame({"salary": salaries, "experience": experience}).dropna()
            if len(pair) >= 3 and pair["salary"].nunique() > 1 and pair["experience"].nunique() > 1:
                results[name]["salary_vs_experience_correlation"] = {
                    "pearson_r": float(pair["salary"].corr(pair["experience"])),
                    "paired_rows": int(len(pair)),
                    "interpretation": "descriptive association; not causal",
                }
        combined.append(frame)

    all_rows = pd.concat(combined, ignore_index=True, sort=False)
    salary_all = pd.concat([_salary_series(frame) for frame in combined], ignore_index=True).dropna()
    exp_cols = [col for col in all_rows.columns if col.endswith("_years_numeric")]
    role_col = _column(list(all_rows.columns), ROLE_TERMS)
    location_col = _column(list(all_rows.columns), LOCATION_TERMS)
    total_records = int(sum(len(df) for df in datasets.values()))
    reported_jobs = int(sum(result["reported_job_count_total"] for result in results.values()))
    summary: dict[str, Any] = {
        "status": "ready",
        "total_jobs": total_records,
        "total_records": total_records,
        "reported_job_count_total": reported_jobs,
        "reported_job_count_note": "Sum of per-row num_of_jobs where supplied; one row counted for sources without that field. Not a deduplicated cross-source vacancy total.",
        "dataset_row_counts": {name: int(len(df)) for name, df in datasets.items()},
        "top_roles": [{"name": name, "count": int(count)} for name, count in role_counter.most_common(12)],
        "top_skills": [{"name": name, "count": int(count)} for name, count in combined_skills.most_common(20)],
        "top_locations": [{"name": name, "count": int(count)} for name, count in location_counter.most_common(12)],
        "locations": [{"name": name, "count": int(count)} for name, count in location_counter.most_common(12)],
        "top_companies": [{"name": name, "count": int(count)} for name, count in company_counter.most_common(12)],
        "top_skill_pairs": [{"skills": list(pair), "cooccurrence_rows": int(count)} for pair, count in combined_skill_pairs.most_common(15)],
        "salary_summary": {
            "unit": "varies by source field; numeric values are not pooled or currency-converted",
            "observed_count": int(salary_all.notna().sum()),
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "by_dataset": {name: result["salary_summary"] for name, result in results.items()},
        },
        "experience_summary": {"unit": "years", "observed_count": int(all_rows[exp_cols].notna().sum().sum()) if exp_cols else 0},
        "notable_relationships": {name: result["salary_vs_experience_correlation"] for name, result in results.items() if result["salary_vs_experience_correlation"]},
        "limitations": [
            "Job postings may not represent the full labor market and can contain duplicates, incomplete fields, or source-specific collection bias.",
            "Salary units and currencies are not converted; unparseable or ambiguous salary values are excluded from numeric summaries.",
            "Observed relationships are descriptive associations and do not identify causal effects.",
            "Column roles are inferred from standardized column names and should be reviewed against the source schema.",
        ],
        "sources": list(datasets),
        "generated_from": list(datasets),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "by_dataset": results,
    }

    _plot_bar(summary["top_roles"], "Top listed job roles", "Rows / reported job counts", figure_dir / "top_roles.png")
    _plot_bar(summary["top_skills"], "Most frequent listed skills", "Mentions", figure_dir / "top_skills.png")
    _plot_bar(summary["top_locations"], "Top job locations", "Postings", figure_dir / "top_locations.png")
    for name, result in results.items():
        salary_counts = result["salary_summary"].get("category_counts", [])
        if salary_counts:
            _plot_bar(salary_counts, f"Salary values — {name} (source categories)", "Rows", figure_dir / f"{name}_salary_bands.png")
    if exp_cols:
        _plot_hist(all_rows[exp_cols].stack().dropna(), "Observed experience requirements", "Experience (years)", figure_dir / "experience_distribution.png")
    for name, result in results.items():
        _plot_bar(result["top_roles"], f"Top roles — {name}", "Postings", figure_dir / f"{name}_roles.png")
        _plot_bar(result["top_skills"], f"Top skills — {name}", "Mentions", figure_dir / f"{name}_skills.png")

    return {"summary": summary, "by_dataset": results, "cleaning_reports": transforms, "job_rows": all_rows}


def _plot_bar(items: list[dict[str, Any]], title: str, ylabel: str, path: Path) -> None:
    if not items:
        return
    ordered = list(reversed(items[:12]))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh([item["name"] for item in ordered], [item["count"] for item in ordered], color="#4f67d8")
    ax.set_title(title)
    ax.set_xlabel(ylabel)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def _plot_hist(values: pd.Series, title: str, xlabel: str, path: Path) -> None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.hist(numeric, bins=min(24, max(6, int(numeric.nunique() ** 0.5))), color="#6377df", edgecolor="white")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Rows")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)

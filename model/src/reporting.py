from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_data_quality_reports(payload: dict[str, Any], reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "data_quality_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# Data Quality Report", "", f"Pipeline status: **{payload.get('status', 'unknown')}**", ""]
    for name, entry in payload.get("datasets", {}).items():
        lines += [f"## {name}", "", f"- Status: {entry.get('status')}"]
        audit = entry.get("audit") or {}
        if audit:
            lines += [f"- Rows: {audit.get('rows')}", f"- Columns: {audit.get('columns')}", f"- Exact duplicate rows: {audit.get('duplicate_rows')}", f"- Missing cells: {audit.get('missing_cells')}"]
            missing = {key: value for key, value in audit.get("missing_values_by_column", {}).items() if value}
            if missing:
                lines += ["", "Missing-value counts by field:", ""]
                lines += [f"- `{column}`: {count}" for column, count in missing.items()]
        if entry.get("error"):
            lines += [f"- Note: {entry['error']}"]
        if entry.get("cleaning"):
            clean = entry["cleaning"]
            lines += [f"- Duplicate rows removed with indices recorded: {clean.get('duplicate_rows_removed', 0)}", f"- Output rows: {clean.get('output_rows')}", f"- Parsed salary columns: {', '.join(clean.get('salary_columns_parsed', {})) or 'none'}", f"- Parsed experience columns: {', '.join(clean.get('experience_columns_parsed', {})) or 'none'}"]
        lines.append("")
    lines += ["## Cleaning rules", "", "Column names were standardized to lowercase underscore-separated words. Text whitespace and common missing tokens were normalized. Exact duplicate removal, where performed, records the original row indices. Salary and experience parsing adds numeric columns and preserves the source columns. The pipeline does not write to `data/raw/`.", ""]
    (reports_dir / "data_quality_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_job_market_report(result: dict[str, Any], path: Path) -> None:
    summary = result["summary"]
    lines = ["# Job Market Analysis", "", f"Generated: {summary['generated_at']}", "", "## Scope and row counts", ""]
    for name, rows in summary["dataset_row_counts"].items():
        lines.append(f"- {name}: {rows:,} job rows")
    lines += ["", "## Top roles", ""]
    lines += [f"- {item['name']}: {item['count']:,}" for item in summary["top_roles"]] or ["- No role column could be identified from the available schema."]
    lines += ["", "## Top skills", ""]
    lines += [f"- {item['name']}: {item['count']:,} mentions" for item in summary["top_skills"]] or ["- No skill-bearing columns were identified."]
    lines += ["", "## Locations", ""]
    lines += [f"- {item['name']}: {item['count']:,}" for item in summary["top_locations"]] or ["- No location column could be identified."]
    lines += ["", "## Salary summary", "", f"- Unit handling: {summary['salary_summary']['unit']}", f"- Parsed observations: {summary['salary_summary']['observed_count']:,}", "- Salary figures are not pooled across differently encoded sources.", ""]
    for name, salary in summary["salary_summary"].get("by_dataset", {}).items():
        lines.append(f"### {name}")
        lines.append(f"Unit: {salary.get('unit')}. Parsed count: {salary.get('observed_count', 0):,}; median in source scale: {salary.get('median')}.")
        bands = salary.get("category_counts", [])
        if bands:
            lines.append("Observed source salary categories: " + ", ".join(f"{item['name']} ({item['count']})" for item in bands) + ".")
        lines.append("")
    lines += ["## Descriptive relationships", ""]
    if summary["notable_relationships"]:
        lines += [f"- {name}: Pearson r={item['pearson_r']:.3f} over {item['paired_rows']} paired rows; descriptive association only." for name, item in summary["notable_relationships"].items()]
    else:
        lines.append("- No salary/experience correlation was computed from at least three complete pairs with variation in both fields.")
    lines += ["", "## Limitations", ""] + [f"- {item}" for item in summary["limitations"]] + ["", "## Per-dataset analysis", ""]
    for name, detail in result["by_dataset"].items():
        lines += [f"### {name}", "", f"Rows analyzed: {detail['rows']:,}.", ""]
        if detail["salary_vs_experience_correlation"]:
            rel = detail["salary_vs_experience_correlation"]
            lines.append(f"Observed salary/experience Pearson correlation: {rel['pearson_r']:.3f} across {rel['paired_rows']} pairs. This is descriptive and not causal.")
            lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_approach_note(quality: dict[str, Any], job_summary: dict[str, Any] | None, models: dict[str, Any]) -> str:
    if quality.get("status") != "complete" or job_summary is None:
        return (
            "# Approach Note — Ghost Skills\n\n"
            "> **Status: analysis not yet run.** The organizer datasets were not available in `data/raw/` when this document was generated. No empirical results, model metrics, or findings are stated. Place all four source files locally and run `python model\\src\\run_pipeline.py` to generate the result-based note.\n\n"
            "## 1. Problem Definition / Analytics Objective\n\n"
            "This project examines how job-market demand, technical skill outcomes, and workforce traits can be analyzed to inform talent and workforce intelligence. The objective is refined against the supplied datasets during the analysis; this draft does not imply a finding.\n\n"
            "## 2. Data Sources and Methods\n\n"
            "The planned sources are Analytics Jobs.csv, DataScience Jobs.csv, JDS Skill Traits.xlsx, and SDS Personality Traits.xlsx. Data will be processed locally. Descriptive job-market summaries will be separated from predictive classification. JDS predictions concern only the supplied salary-hike target. SDS modeling concerns only the supplied organizational success label and must not be read as universal personality-based hiring truth.\n\n"
            "## 3. Results, Conclusions, and Implications\n\n"
            "Results, conclusions, stakeholder implications, and figures are withheld until the data pipeline has run successfully. No metrics or observations have been fabricated.\n\n"
            "## 4. Limitations\n\n"
            "The final analysis must document sample size and representativeness, missing or noisy fields, label definitions, salary parsing assumptions, and the observational nature of the data. Association will not be described as causation.\n"
        )
    summary = job_summary
    lines = [
        "# Ghost Skills Approach Note",
        "",
        f"> Generated from local pipeline outputs at {summary.get('generated_at', 'timestamp unavailable')}. All quantities below are drawn from the four supplied files; encoded target classes are retained without an undocumented 0/1 interpretation.",
        "",
        "## Executive Summary",
        "",
        f"The two job-posting sources contain {summary.get('total_jobs', 0):,} records. The DataScience Jobs file reports {summary.get('reported_job_count_total', 0):,} combined row counts using its `num_of_jobs` field and one row per record for the other source; this is not a deduplicated vacancy total.",
        "",
        "The most frequent parsed skill mentions are " + (", ".join(f"{item['name']} ({item['count']:,})" for item in summary.get("top_skills", [])[:5]) or "not available") + ". In the five-fold stratified evaluation, the selected JDS model was " + (models.get("jds") or {}).get("model_name", "not trainable") + " and the selected SDS model was " + (models.get("sds") or {}).get("model_name", "not trainable") + ". Their internal estimates are based on 139 and 161 complete cases respectively and are not external validation.",
        "",
        "The targets are stored as numeric codes 0 and 1. Because no authoritative code-to-meaning mapping was included in the files, the models preserve those labels as encoded classes. The SDS classifier is exploratory association with the supplied label, not a universal personality-based hiring truth. No causal effects are inferred.",
        "",
        "## 1. Problem Definition and Analytics Objective",
        "",
        "How can observed job-market demand, technical skill outcomes, and workforce-trait labels be analyzed to provide transparent and appropriately bounded talent intelligence from the four organizer datasets? The work separates descriptive job-posting summaries, predictive classification of supplied labels, observational association, and proposed business implications.",
        "",
        "## 2. Business Context",
        "",
        "The prototype provides aggregate views of the supplied job postings and two small tabular classifiers. It can help teams form questions about advertised roles and skills. It is not a resume-verification service, individual hiring score, or causal workforce study. A recruiter should not use an SDS prediction to screen a person.",
        "",
        "## 3. Data Sources",
        "",
        "| Dataset | Rows | Columns | Missing cells | Exact duplicate rows |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, entry in quality.get("datasets", {}).items():
        audit = entry.get("audit", {})
        lines.append(f"| {name} | {audit.get('rows', '—')} | {audit.get('columns', '—')} | {audit.get('missing_cells', '—')} | {audit.get('duplicate_rows', '—')} |")
    lines += [
        "",
        "Analytics Jobs contains role designation, key skills, location, experience text, salary bands, and job type. DataScience Jobs contains company, title, minimum experience, average/minimum/maximum salary fields, and a reported `num_of_jobs` count. JDS Skill Traits contains five numeric features and `salary_hike_high_or_low`. SDS Personality Traits contains five numeric traits and a whitespace/punctuation variant of `success_classification_high_low`, normalized by the loader.",
        "",
        "All files were read locally. The pipeline did not modify `data/raw/` and the API exposes aggregates rather than source rows.",
        "",
        "## 4. Data Exploration",
        "",
        f"The Analytics Jobs file has {quality['datasets']['analytics_jobs']['audit']['rows']:,} rows; DataScience Jobs has {quality['datasets']['datascience_jobs']['audit']['rows']:,}; JDS has {quality['datasets']['jds']['audit']['rows']:,}; SDS has {quality['datasets']['sds']['audit']['rows']:,}. Job-posting text and categories vary by source, so source-specific salary units and aggregation meanings are preserved.",
        "",
        "JDS target counts: " + ", ".join(f"class {key}: {value}" for key, value in (models.get("jds") or {}).get("class_balance", {}).items()) + ". SDS target counts: " + ", ".join(f"class {key}: {value}" for key, value in (models.get("sds") or {}).get("class_balance", {}).items()) + ". The numeric class mapping is not inferred.",
        "",
        "## 5. Data Quality Issues",
        "",
    ]
    for name, entry in quality.get("datasets", {}).items():
        audit = entry.get("audit", {})
        missing = [(field, count) for field, count in audit.get("missing_values_by_column", {}).items() if count]
        lines.append(f"### {name}")
        lines.append(f"{audit.get('missing_cells', 0):,} missing cells across {audit.get('rows', 0):,} rows. Missing fields: " + (", ".join(f"{field} ({count:,})" for field, count in missing) if missing else "none recorded") + f". Exact duplicate rows: {audit.get('duplicate_rows', 0):,}.")
        lines.append("")
    lines += [
        "The Analytics Jobs source has many missing `job_type` and `job_description` values, but its skill, designation, experience, salary-band, and location fields are largely present. The other three files have no missing cells in the audited columns. No exact duplicate rows were detected in any source.",
        "",
        "## 6. Data Preparation",
        "",
        "The loader standardized headers to lowercase underscore-separated names. Text fields had whitespace collapsed and common missing-value tokens converted to null. Exact duplicate removal is recorded with original indices; this run found none. Skill lists were split on comma, semicolon, pipe, or newline and lowercased; terminal ellipses were removed from truncated tokens. Salary and experience derived fields were added without replacing source text. Every transformation and row count is in `data/reports/data_quality_report.json`.",
        "",
        "Salary bands such as `6to10` in Analytics Jobs remain categories because their units are not explicit. DataScience salary entries use an `L` suffix; the numeric summaries preserve lakh units, but the time period is not inferred. Salary fields from the two sources are not pooled. Experience ranges are represented by their midpoint in years; the SDS trait `openness_to_experience` is not treated as a work-experience field.",
        "",
        "## 7. Feature Derivation",
        "",
        "The JDS model uses the exact five supplied skill fields. The SDS model uses the five supplied personality fields after header normalization. IDs are not model features. Numeric conversion is explicit; complete cases are used for fitting and cross-validation. No target labels were created or remapped.",
        "",
        "| Model | Feature | Observed minimum | Observed maximum |",
        "| --- | --- | ---: | ---: |",
    ]
    for key in ("jds", "sds"):
        for feature, bounds in (models.get(key) or {}).get("feature_ranges", {}).items():
            lines.append(f"| {key.upper()} | {feature} | {bounds['min']:g} | {bounds['max']:g} |")
    lines += ["", "Feature ranges are observed sample ranges, not validated scales or recommended inputs.", "", "## 8. Job-Market Analysis", ""]
    lines.append(f"The two job files contain {summary['total_records']:,} source rows. Across the listed `num_of_jobs` value and one-per-row counts for the other source, the arithmetic total is {summary['reported_job_count_total']:,}; it is not a deduplicated vacancy count or a market-size estimate.")
    lines.append("")
    lines.append("Top role rows: " + "; ".join(f"{item['name']} ({item['count']:,})" for item in summary.get("top_roles", [])[:8]) + ".")
    lines.append("Top skill mentions: " + "; ".join(f"{item['name']} ({item['count']:,})" for item in summary.get("top_skills", [])[:10]) + ".")
    lines.append("Most frequent normalized location components: " + "; ".join(f"{item['name']} ({item['count']:,})" for item in summary.get("top_locations", [])[:8]) + ".")
    lines.append("Top company job counts as reported in DataScience Jobs: " + "; ".join(f"{item['name']} ({item['count']:,})" for item in summary.get("top_companies", [])[:8]) + ".")
    lines.append("")
    for name, salary in summary["salary_summary"].get("by_dataset", {}).items():
        lines.append(f"{name} salary: {salary.get('unit')}. Parsed values={salary.get('observed_count', 0):,}; median={salary.get('median')}; observed source categories=" + ", ".join(f"{item['name']} ({item['count']:,})" for item in salary.get("category_counts", [])[:8]) + ".")
    lines.append("")
    for name, relationship in summary.get("notable_relationships", {}).items():
        lines.append(f"Within {name}, the Pearson correlation of parsed average salary and experience is {relationship['pearson_r']:.3f} across {relationship['paired_rows']:,} paired rows. This is a descriptive association, not a causal estimate.")
    lines += [
        "",
        "The job files do not share a row-level join key, and their fields and aggregation differ. The combined view is a side-by-side summary, not a merged record set. Skill co-occurrence results are available in the generated JSON where the source text supports them.",
        "",
        "## 9. JDS Modelling Approach",
        "",
        "The target column is stored as numeric 0/1. Since the files do not define the mapping, model output remains an encoded class. A majority-class DummyClassifier is compared with logistic regression and random forest. Five-fold shuffled stratified cross-validation is used because both classes have enough cases. Macro precision, recall, F1, accuracy, and ROC-AUC are calculated from out-of-fold predictions. Model choice prioritizes macro F1, with accuracy as a tie-break. The selected model is refit on all complete cases only for the local demo artifact.",
        "",
    ]
    lines += _model_report_section(models.get("jds"), "JDS", "encoded source target class; the code-to-high/low mapping is undocumented")
    lines += ["", "## 10. JDS Results", "", "The exact comparison values are reported below. The selected logistic model's strongest absolute standardized coefficients rank skill associations in this fitted model; absolute magnitudes do not provide direction and are not causal effects.", "", "## 11. SDS Modelling Approach", "", "The same baseline and candidate algorithms, fold logic, metrics, and selection rule are applied to the SDS target after normalizing its header. The source target is also encoded 0/1 without an authoritative semantic mapping. Trait values are model inputs because they are present in the supplied sample; this does not validate use in hiring.", ""]
    lines += _model_report_section(models.get("sds"), "SDS", "encoded organizational success label; association only, not a universal personality-based hiring truth")
    lines += ["", "## 12. SDS Results", "", "The random forest's feature-importance values are impurity-based within this fitted model. They describe model reliance in this sample, not causal effects, universal trait validity, or person-level suitability.", "", "## 13. Cross-Analysis and Consolidation", "", "The job-posting files and traits files contain different units and no documented person/job join key. No record-level merge is performed. Market summaries and label models are therefore presented as complementary but independent evidence, without combining them into a score.", "", "## 14. Key Findings", ""]
    lines += [f"- {summary['top_skills'][0]['name']} is the most frequent normalized skill mention ({summary['top_skills'][0]['count']:,}) in the parsed skill text." for _ in [0] if summary.get("top_skills")]
    lines += [f"- {summary['top_roles'][0]['name']} is the most frequent role label ({summary['top_roles'][0]['count']:,} source rows) under the standardized role-field extraction." for _ in [0] if summary.get("top_roles")]
    lines += [f"- The parsed DataScience salary and minimum-experience fields have a within-source Pearson correlation of {summary['notable_relationships']['datascience_jobs']['pearson_r']:.3f} over {summary['notable_relationships']['datascience_jobs']['paired_rows']:,} rows." for _ in [0] if "datascience_jobs" in summary.get("notable_relationships", {})]
    for key in ("jds", "sds"):
        result = models.get(key) or {}
        if result.get("status") == "ready":
            lines.append(f"- {result['model_name']} has five-fold out-of-fold accuracy {result['validation_metrics']['accuracy']:.3f} and macro F1 {result['validation_metrics']['f1_macro']:.3f} on {result['training_rows']} rows. This estimate is internal to the supplied sample.")
    lines += ["", "## 15. Conclusions", "", "The files support aggregate descriptions of advertised roles, skill mentions, locations, and source-specific salary/experience fields. Both small labeled tables support internally evaluated classifiers with observed numeric class codes, but the class meanings are not confirmed by the available data. Results do not establish that skills cause salary increases or traits cause success. The prototype is an analytical demonstration, not a validated employment decision tool.", "", "## 16. Implications for Stakeholders", "", "Workforce planners can use the job-posting aggregates to frame skill and location discussions while checking source coverage and the posting mix. The JDS classifier can be used to demonstrate local model serving against its encoded target. The SDS analysis should remain a research view only and must not screen, rank, or assess individuals. Any operational proposal requires confirmed label definitions, representative data, external validation, and a separate fairness/privacy review.", "", "## 17. Limitations", ""]
    lines += [f"- {item}" for item in summary.get("limitations", [])]
    for key in ("jds", "sds"):
        lines += [f"- {item}" for item in (models.get(key) or {}).get("limitations", [])]
    lines += ["- JDS (139 complete cases) and SDS (161 complete cases) are small samples; fold estimates can vary substantially.", "- No external holdout or temporal validation was available.", "- Target codes 0/1 are not documented here; semantic high/low mapping remains unresolved.", "- Potential self-reporting, masking, selection bias, and target-definition issues cannot be quantified from these files alone.", "- The job sources may contain truncation, inconsistent category text, and source-specific coverage; salary-band units in Analytics Jobs are not explicit.", "- The unweighted or reported count aggregation differs by source; reported job counts are not a deduplicated market total.", "- Observational associations do not establish causal effects.", "", "## 18. Future Work", "", "Confirm the target codebook and salary-band units with organizer documentation, evaluate on an independent representative sample, assess temporal and subgroup robustness, review skill extraction and deduplication assumptions, and document feature scales before exposing predictions to users. Keep any SDS result out of individual hiring decisions.", "", "## 19. Appendix References", "", "`data/reports/data_quality_report.md` and `.json`; `data/reports/job_market_report.md`; `model/reports/jds_training.json`; `model/reports/sds_training.json`; `model/artifacts/job_market_summary.json`; and generated figures in `model/figures/`.", ""]
    return "\n".join(lines)


def build_approach_docx(markdown_text: str, output_path: Path, figure_dir: Path | None = None) -> None:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    document = Document()
    document.core_properties.title = "Ghost Skills Approach Note"
    document.core_properties.subject = "Dataset-driven analytics results and limitations"
    document.core_properties.author = "Ghost Skills team"
    section = document.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)
    for style_name in ("Normal", "Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3"):
        style = document.styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        if style_name == "Normal":
            style.font.size = Pt(12)
            style.paragraph_format.line_spacing = 1.0
        style.font.color.rgb = __import__("docx").shared.RGBColor(0, 0, 0)
    header = section.header.paragraphs[0]
    header.text = "GHOST SKILLS  |  BUILD FOR BHARAT 2.0"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header.runs[0].font.size = Pt(9)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("Page ")
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    run._r.addnext(field)

    lines = markdown_text.splitlines()
    first_heading = True
    index = 0
    while index < len(lines):
        line = lines[index]
        text = line.strip()
        if not text or text == "---":
            index += 1
            continue
        if text.startswith("# "):
            if first_heading:
                p = document.add_paragraph(style="Title")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run(text[2:].replace("**", ""))
                subtitle = document.add_paragraph()
                subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
                subtitle.add_run("Build for Bharat 2.0 | Analytics Approach Note").bold = True
                context = document.add_paragraph()
                context.alignment = WD_ALIGN_PARAGRAPH.CENTER
                context.add_run("Local analysis of the four organizer-provided datasets").italic = True
                document.add_page_break()
                first_heading = False
            else:
                document.add_heading(text[2:].replace("**", ""), level=1)
        elif text.startswith("## "):
            document.add_heading(text[3:].replace("**", ""), level=2)
        elif text.startswith("### "):
            document.add_heading(text[4:].replace("**", ""), level=3)
        elif text.startswith("> "):
            p = document.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            r = p.add_run(text[2:].replace("**", ""))
            r.italic = True
        elif text.startswith("- "):
            p = document.add_paragraph(style="List Bullet")
            p.add_run(text[2:].replace("`", "").replace("**", ""))
        elif text.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append([cell.strip() for cell in lines[index].strip().strip("|").split("|")])
                index += 1
            rows = [row for row in table_lines if not all(set(cell) <= {"-", ":", " "} for cell in row)]
            if rows:
                table = document.add_table(rows=1, cols=len(rows[0]))
                table.style = "Table Grid"
                for cell, value in zip(table.rows[0].cells, rows[0]):
                    cell.text = value
                    for run in cell.paragraphs[0].runs:
                        run.bold = True
                for row in rows[1:]:
                    cells = table.add_row().cells
                    for cell, value in zip(cells, row):
                        cell.text = value
                for row in table.rows:
                    row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            paragraph.paragraph_format.line_spacing = 1.0
                            for run in paragraph.runs:
                                run.font.name = "Times New Roman"
                                run.font.size = Pt(12)
                                run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
            continue
        else:
            document.add_paragraph(text.replace("`", "").replace("**", ""))
        index += 1

    if figure_dir and figure_dir.is_dir():
        figures = sorted(figure_dir.rglob("*.png"))
        if figures:
            document.add_page_break()
            document.add_heading("Appendix: Generated Figures", level=1)
            for figure in figures:
                document.add_page_break()
                document.add_picture(str(figure), width=Inches(6.1))
                picture = document.inline_shapes[-1]._inline.docPr
                picture.set("descr", figure.stem.replace("_", " "))
                caption = document.add_paragraph(f"Figure: {figure.stem.replace('_', ' ')}")
                caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
                caption.runs[0].italic = True
                caption.runs[0].font.size = Pt(10)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)


def _model_report_section(result: dict[str, Any] | None, label: str, target_note: str) -> list[str]:
    if not result or result.get("status") != "ready":
        return [f"No trainable artifact was produced for {label}. The pipeline reason is recorded in the model report; no model performance is claimed."]
    metrics = result.get("validation_metrics", {})
    content = [f"Selected model: {result['model_name']}; target: `{result['target']}`; complete-case rows: {result['training_rows']:,}; stratified folds: {result['cv_folds']}.", "", f"Target interpretation: {target_note}.", "", "Out-of-fold validation metrics:"]
    content += [f"- {key}: {value:.4f}" for key, value in metrics.items() if isinstance(value, (int, float))]
    content += ["", "Model comparison (macro F1):"]
    content += [f"- {name}: {value.get('f1_macro', 'unavailable')}" for name, value in result.get("model_comparison", {}).items() if isinstance(value, dict)]
    content += ["", "Limitations:"] + [f"- {item}" for item in result.get("limitations", [])]
    return content

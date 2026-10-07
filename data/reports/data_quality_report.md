# Data Quality Report

Pipeline status: **complete**

## analytics_jobs

- Status: loaded
- Rows: 15841
- Columns: 8
- Exact duplicate rows: 0
- Missing cells: 15520

Missing-value counts by field:

- `job_description`: 3508
- `job_type`: 12011
- `key_skills`: 1
- Duplicate rows removed with indices recorded: 0
- Output rows: 15841
- Parsed salary columns: none
- Parsed experience columns: experience

## datascience_jobs

- Status: loaded
- Rows: 1602
- Columns: 8
- Exact duplicate rows: 0
- Missing cells: 0
- Duplicate rows removed with indices recorded: 0
- Output rows: 1602
- Parsed salary columns: avg_salary, min_salary, max_salary
- Parsed experience columns: min_experience

## jds

- Status: loaded
- Rows: 139
- Columns: 7
- Exact duplicate rows: 0
- Missing cells: 0
- Duplicate rows removed with indices recorded: 0
- Output rows: 139
- Parsed salary columns: none
- Parsed experience columns: none

## sds

- Status: loaded
- Rows: 161
- Columns: 7
- Exact duplicate rows: 0
- Missing cells: 0
- Duplicate rows removed with indices recorded: 0
- Output rows: 161
- Parsed salary columns: none
- Parsed experience columns: none

## Cleaning rules

Column names were standardized to lowercase underscore-separated words. Text whitespace and common missing tokens were normalized. Exact duplicate removal, where performed, records the original row indices. Salary and experience parsing adds numeric columns and preserves the source columns. The pipeline does not write to `data/raw/`.

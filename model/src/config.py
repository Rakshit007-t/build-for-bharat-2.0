from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DATA_REPORTS_DIR = ROOT / "data" / "reports"
ARTIFACTS_DIR = ROOT / "model" / "artifacts"
FIGURES_DIR = ROOT / "model" / "figures"
MODEL_REPORTS_DIR = ROOT / "model" / "reports"

DATASETS = {
    "analytics_jobs": "Analytics Jobs.csv",
    "datascience_jobs": "DataScience Jobs.csv",
    "jds": "JDS Skill Traits.xlsx",
    "sds": "SDS Personality Traits.xlsx",
}

JDS_FEATURES = [
    "big_data_skills",
    "maths_stats_skills",
    "coding_skills",
    "ai_and_ml_skills",
    "dashboard_and_storytelling_skills",
]
SDS_FEATURES = [
    "neuroticism",
    "extraversion",
    "openness_to_experience",
    "agreeableness",
    "conscientiousness",
]

TARGETS = {
    "jds": "salary_hike_high_or_low",
    "sds": "success_classification_high_low",
}

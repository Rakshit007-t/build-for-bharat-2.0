from pathlib import Path

import pandas as pd

from model.src.config import JDS_FEATURES, TARGETS
from model.src.evaluation import evaluate_binary_model


LIMITATIONS = [
    "The target records the supplied salary-hike class and may reflect a narrow sample or a dataset-specific definition.",
    "Cross-validation is internal to the supplied dataset; it does not establish performance on other organizations or populations.",
    "Skill scores are observational inputs; associations are not evidence that a skill causes salary growth.",
]


def train_jds(frame: pd.DataFrame, artifacts_dir: Path) -> dict:
    return evaluate_binary_model(frame, JDS_FEATURES, TARGETS["jds"], artifacts_dir, "jds", LIMITATIONS)

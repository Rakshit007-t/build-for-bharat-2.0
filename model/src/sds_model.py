from pathlib import Path

import pandas as pd

from model.src.config import SDS_FEATURES, TARGETS
from model.src.evaluation import evaluate_binary_model


LIMITATIONS = [
    "The target is the success label supplied in this dataset, not universal or independently verified career success.",
    "Personality-trait associations do not show that personality causes organizational success.",
    "The model must not be treated as a hiring score or used to make individual employment decisions.",
    "Cross-validation is internal to the supplied sample and may be unstable for small class counts.",
]


def train_sds(frame: pd.DataFrame, artifacts_dir: Path) -> dict:
    return evaluate_binary_model(frame, SDS_FEATURES, TARGETS["sds"], artifacts_dir, "sds", LIMITATIONS)

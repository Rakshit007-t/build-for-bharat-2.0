from __future__ import annotations

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def candidate_estimators(seed: int = 42) -> dict[str, Any]:
    return {
        "majority_baseline": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=seed)),
        ]),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            class_weight=None,
            random_state=seed,
        ),
    }


def evaluate_binary_model(
    frame,
    feature_names: list[str],
    target_name: str,
    output_dir: Path,
    model_prefix: str,
    limitations: list[str],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir.parent / "figures" / model_prefix
    figure_dir.mkdir(parents=True, exist_ok=True)
    data = frame[feature_names + [target_name]].dropna().copy()
    data[feature_names] = data[feature_names].apply(lambda col: __import__("pandas").to_numeric(col, errors="coerce"))
    data = data.dropna(subset=feature_names)
    classes = list(data[target_name].astype(str).unique())
    if len(classes) != 2:
        return {"status": "not_trainable", "reason": "Target does not contain exactly two observed classes.", "rows_used": int(len(data)), "observed_labels": classes, "limitations": limitations}
    counts = data[target_name].astype(str).value_counts()
    min_class = int(counts.min())
    if min_class < 2:
        return {"status": "not_trainable", "reason": "Stratified cross-validation requires at least two observations in each class.", "rows_used": int(len(data)), "class_balance": counts.to_dict(), "limitations": limitations}

    X = data[feature_names].astype(float)
    X_values = X.to_numpy()
    y = data[target_name].astype(str).str.strip().str.lower()
    # Preserve encoded labels such as 0/1; never assume which code means "high".
    folds = min(5, min_class)
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
    comparisons: dict[str, Any] = {}
    predictions: dict[str, Any] = {}
    for name, estimator in candidate_estimators().items():
        try:
            pred = cross_val_predict(clone(estimator), X_values, y, cv=cv, method="predict")
            metrics: dict[str, Any] = {
                "accuracy": float(accuracy_score(y, pred)),
                "precision_macro": float(precision_score(y, pred, average="macro", zero_division=0)),
                "recall_macro": float(recall_score(y, pred, average="macro", zero_division=0)),
                "f1_macro": float(f1_score(y, pred, average="macro", zero_division=0)),
            }
            if name != "majority_baseline":
                try:
                    proba = cross_val_predict(clone(estimator), X_values, y, cv=cv, method="predict_proba")
                    metrics["roc_auc"] = float(roc_auc_score(y, proba[:, 1]))
                except (AttributeError, ValueError, IndexError):
                    metrics["roc_auc"] = None
            comparisons[name] = metrics
            predictions[name] = pred
        except Exception as exc:
            comparisons[name] = {"error": f"Cross-validation failed: {type(exc).__name__}"}

    viable = [name for name in comparisons if name in predictions and name != "majority_baseline"]
    if not viable:
        return {"status": "not_trainable", "reason": "No candidate model completed cross-validation.", "rows_used": int(len(data)), "class_balance": counts.to_dict(), "model_comparison": comparisons, "limitations": limitations}
    selected_name = max(viable, key=lambda name: (comparisons[name]["f1_macro"], comparisons[name]["accuracy"]))
    selected = candidate_estimators()[selected_name]
    selected.fit(X_values, y)
    model_path = output_dir / f"{model_prefix}_model.pkl"
    with model_path.open("wb") as file:
        pickle.dump(selected, file)

    labels = sorted(y.unique())
    matrix = confusion_matrix(y, predictions[selected_name], labels=labels)
    figure, axis = plt.subplots(figsize=(5.6, 4.6))
    axis.imshow(matrix, cmap="Blues")
    axis.set_title(f"{model_prefix.upper()} out-of-fold confusion matrix")
    axis.set_xlabel("Predicted label")
    axis.set_ylabel("Observed label")
    axis.set_xticks(range(len(labels)), labels=labels)
    axis.set_yticks(range(len(labels)), labels=labels)
    for (row, col), value in np.ndenumerate(matrix):
        axis.text(col, row, str(value), ha="center", va="center", color="black")
    figure.tight_layout()
    figure.savefig(figure_dir / "confusion_matrix.png", dpi=170)
    plt.close(figure)

    importance: dict[str, float] = {}
    if selected_name == "random_forest":
        importance = dict(zip(feature_names, map(float, selected.feature_importances_)))
    elif selected_name == "logistic_regression":
        coefs = selected.named_steps["classifier"].coef_[0]
        importance = dict(zip(feature_names, map(float, np.abs(coefs))))
    if importance:
        ordered = sorted(importance.items(), key=lambda item: item[1])
        figure, axis = plt.subplots(figsize=(7, 4.8))
        axis.barh([item[0].replace("_", " ") for item in ordered], [item[1] for item in ordered], color="#536dfe")
        axis.set_title("Model feature importance (magnitude)")
        axis.set_xlabel("Importance" if selected_name == "random_forest" else "Absolute standardized coefficient")
        figure.tight_layout()
        figure.savefig(figure_dir / "feature_importance.png", dpi=170)
        plt.close(figure)

    corr = X.corr(numeric_only=True)
    figure, axis = plt.subplots(figsize=(6.4, 5.4))
    image = axis.imshow(corr.to_numpy(), cmap="coolwarm", vmin=-1, vmax=1)
    axis.set_xticks(range(len(feature_names)), [name.replace("_", " ") for name in feature_names], rotation=45, ha="right")
    axis.set_yticks(range(len(feature_names)), [name.replace("_", " ") for name in feature_names])
    axis.set_title("Feature correlation (descriptive)")
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    figure.tight_layout()
    figure.savefig(figure_dir / "correlations.png", dpi=170)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(7, 4.5))
    names = list(comparisons)
    values = [comparisons[name].get("f1_macro", float("nan")) for name in names]
    axis.bar(names, values, color=["#90a4ae", "#5c6bc0", "#26a69a"][:len(names)])
    axis.set_ylim(0, 1)
    axis.set_ylabel("Macro F1 (stratified out-of-fold)")
    axis.set_title("Model comparison")
    axis.tick_params(axis="x", rotation=15)
    figure.tight_layout()
    figure.savefig(figure_dir / "model_comparison.png", dpi=170)
    plt.close(figure)

    metadata = {
        "model_name": f"{model_prefix.upper()} {selected_name.replace('_', ' ').title()}",
        "model_version": "1.0.0",
        "algorithm": selected_name,
        "training_rows": int(len(data)),
        "feature_names": feature_names,
        "target": target_name,
        "class_labels": labels,
        "class_balance": {str(label): int(count) for label, count in counts.items()},
        "confusion_matrix": {"labels": [str(label) for label in labels], "values": matrix.tolist()},
        "class_label_interpretation": "Observed source labels are preserved as-is; numeric codes are not remapped to semantic high/low labels without an authoritative mapping.",
        "validation_metrics": comparisons[selected_name],
        "model_comparison": comparisons,
        "preprocessing_steps": ["numeric coercion", "complete-case filtering for model features and target", "stratified cross-validation"],
        "feature_ranges": {name: {"min": float(X[name].min()), "max": float(X[name].max())} for name in feature_names},
        "feature_importance": importance,
        "cv_folds": folds,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "limitations": limitations + ["Cross-validation estimates may be unstable for a small or non-representative sample."],
    }
    (output_dir / f"{model_prefix}_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    figure, axis = plt.subplots(figsize=(6, 4.5))
    counts.plot(kind="bar", ax=axis, color="#7986cb")
    axis.set_title(f"{model_prefix.upper()} observed target class balance")
    axis.set_ylabel("Rows")
    axis.tick_params(axis="x", rotation=0)
    figure.tight_layout()
    figure.savefig(figure_dir / "class_balance.png", dpi=170)
    plt.close(figure)

    return {"status": "ready", **metadata}

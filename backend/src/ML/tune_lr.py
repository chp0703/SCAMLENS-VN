"""Tune Logistic Regression on the shared predefined ML cross-validation folds.

The test split is deliberately excluded from this module.  GridSearchCV fits
the TF-IDF pipeline only on each CV training fold, then refits the F1-selected
estimator on the complete shared ML training pool for local artifact storage.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import warnings

import joblib
import numpy as np
import sklearn
from sklearn.metrics import f1_score, make_scorer, precision_score, recall_score
from sklearn.model_selection import GridSearchCV, ParameterGrid

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ML.data_utils import MLData, load_ml_data
from src.ML.models.logistic_regression import build_lr_pipeline


PARAM_GRID = {
    "model__C": [0.01, 0.1, 1, 10, 100],
    "model__class_weight": [None, "balanced"],
}
SCORING = {
    "f1_scam": make_scorer(f1_score, pos_label=1, zero_division=0),
    "precision_scam": make_scorer(precision_score, pos_label=1, zero_division=0),
    "recall_scam": make_scorer(recall_score, pos_label=1, zero_division=0),
}
METRICS = ("f1_scam", "precision_scam", "recall_scam")
METRIC_LABELS = {
    "f1_scam": "F1 (Scam, pos_label=1)",
    "precision_scam": "Precision (Scam, pos_label=1)",
    "recall_scam": "Recall (Scam, pos_label=1)",
}


@dataclass(frozen=True)
class ArtifactResult:
    """Locations and smoke-check output for a saved local artifact."""

    model_path: Path
    metadata_path: Path
    smoke_predictions: tuple[int, ...]


@dataclass(frozen=True)
class TuningResult:
    """Selected GridSearchCV result and Scam-focused CV measurements."""

    search: GridSearchCV
    best_params: dict
    best_index: int
    fold_ids: tuple[int, ...]
    per_fold_scores: dict[str, tuple[float, ...]]
    means: dict[str, float]
    standard_deviations: dict[str, float]
    candidate_count: int
    cv_fit_count: int
    warnings: tuple[str, ...]
    artifact: ArtifactResult | None = None

    @property
    def best_estimator(self):
        """The F1-selected estimator refitted on all shared ML training rows."""
        return self.search.best_estimator_


def _default_artifact_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "artifacts" / "logistic_regression"


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "splits" / "ml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_fingerprints(data_dir: str | Path | None) -> dict[str, str]:
    """Fingerprint only shared split artifacts, never message content."""
    directory = (Path(data_dir) if data_dir is not None else _default_data_dir()).resolve()
    result = {}
    for filename in ("train.csv", "cv_folds.csv"):
        path = directory / filename
        if path.is_file():
            result[filename] = _sha256(path)
    return result


def tune_data(data: MLData) -> TuningResult:
    """Run the fixed 10-candidate GridSearchCV solely on shared train data."""
    search = GridSearchCV(
        estimator=build_lr_pipeline(),
        param_grid=PARAM_GRID,
        scoring=SCORING,
        refit="f1_scam",
        cv=data.cv,
        return_train_score=False,
        error_score="raise",
        n_jobs=1,
    )
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        search.fit(data.X_train, data.y_train)

    best_index = int(search.best_index_)
    cv_results = search.cv_results_
    fold_ids = tuple(sorted({int(fold) for fold in data.fold_ids}))
    per_fold_scores = {
        metric: tuple(float(cv_results[f"split{fold}_test_{metric}"][best_index]) for fold in fold_ids)
        for metric in METRICS
    }
    means = {metric: float(cv_results[f"mean_test_{metric}"][best_index]) for metric in METRICS}
    standard_deviations = {metric: float(cv_results[f"std_test_{metric}"][best_index]) for metric in METRICS}
    warning_messages = tuple(
        f"{warning.category.__name__}: {warning.message}"
        for warning in caught_warnings
    )
    candidate_count = len(cv_results["params"])
    return TuningResult(
        search=search,
        best_params=dict(search.best_params_),
        best_index=best_index,
        fold_ids=fold_ids,
        per_fold_scores=per_fold_scores,
        means=means,
        standard_deviations=standard_deviations,
        candidate_count=candidate_count,
        cv_fit_count=candidate_count * len(fold_ids),
        warnings=warning_messages,
    )


def save_best_artifact(
    result: TuningResult,
    data: MLData,
    artifact_dir: str | Path | None = None,
    source_fingerprints: dict[str, str] | None = None,
) -> ArtifactResult:
    """Persist the refitted best estimator plus safe, reproducible metadata."""
    directory = (Path(artifact_dir) if artifact_dir is not None else _default_artifact_dir()).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    model_path = directory / "model.joblib"
    metadata_path = directory / "metadata.json"
    joblib.dump(result.best_estimator, model_path)

    reloaded_model = joblib.load(model_path)
    smoke_predictions = tuple(int(value) for value in reloaded_model.predict(["xin chao", "nhan thuong gap"]))
    metadata = {
        "model_name": "Logistic Regression TF-IDF Pipeline",
        "pipeline_components": list(result.best_estimator.named_steps),
        "best_hyperparameters": result.best_params,
        "selection_metric": "f1_scam",
        "scoring": {
            "f1_scam": "f1_score(pos_label=1, zero_division=0)",
            "precision_scam": "precision_score(pos_label=1, zero_division=0)",
            "recall_scam": "recall_score(pos_label=1, zero_division=0)",
        },
        "parameter_grid": PARAM_GRID,
        "selected_cv_metrics": {
            metric: {
                "mean": result.means[metric],
                "standard_deviation": result.standard_deviations[metric],
                "per_fold": list(result.per_fold_scores[metric]),
            }
            for metric in METRICS
        },
        "candidate_count": result.candidate_count,
        "cv_fit_count": result.cv_fit_count,
        "training_samples": len(data.X_train),
        "cv": {
            "type": "PredefinedSplit",
            "fold_ids": list(result.fold_ids),
            "shared_fold_assignments": True,
        },
        "label_mapping": {"0": "Ham", "1": "Scam"},
        "versions": {"python": platform.python_version(), "scikit_learn": sklearn.__version__},
        "source_sha256": source_fingerprints or {},
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ArtifactResult(model_path, metadata_path, smoke_predictions)


def run_tuning(
    data_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
    save_artifact: bool = True,
) -> TuningResult:
    """Load data, tune using shared CV, and optionally save the refitted model."""
    data = load_ml_data(data_dir=data_dir, manifest_path=manifest_path)
    result = tune_data(data)
    if not save_artifact:
        return result
    artifact = save_best_artifact(result, data, artifact_dir, _source_fingerprints(data_dir))
    return replace(result, artifact=artifact)


def format_tuning_result(result: TuningResult) -> str:
    """Format candidate and selected metrics without exposing training text."""
    lines = [
        f"Logistic Regression tuning: {result.candidate_count} candidates, "
        f"{result.cv_fit_count} predefined CV fits",
        "Candidates (mean +/- population std):",
    ]
    cv_results = result.search.cv_results_
    for index, params in enumerate(cv_results["params"]):
        metrics = ", ".join(
            f"{METRIC_LABELS[metric]}={cv_results[f'mean_test_{metric}'][index]:.4f} +/- "
            f"{cv_results[f'std_test_{metric}'][index]:.4f}"
            for metric in METRICS
        )
        lines.append(f"  {index}: {params}; {metrics}")
    lines.append(f"Best parameters (selected by F1 Scam): {result.best_params}")
    for index, fold_id in enumerate(result.fold_ids):
        metrics = ", ".join(
            f"{METRIC_LABELS[metric]}={result.per_fold_scores[metric][index]:.4f}"
            for metric in METRICS
        )
        lines.append(f"Best candidate fold {fold_id}: {metrics}")
    lines.append("Best candidate aggregate (mean +/- population std):")
    for metric in METRICS:
        lines.append(
            f"  {METRIC_LABELS[metric]}: {result.means[metric]:.4f} +/- "
            f"{result.standard_deviations[metric]:.4f}"
        )
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"  {warning}" for warning in result.warnings)
    else:
        lines.append("Warnings: none")
    if result.artifact:
        lines.append(f"Saved model: {result.artifact.model_path}")
        lines.append(f"Saved metadata: {result.artifact.metadata_path}")
        lines.append(f"Reload smoke predictions: {list(result.artifact.smoke_predictions)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="Directory containing ML train.csv, test.csv, and cv_folds.csv")
    parser.add_argument("--manifest", type=Path, help="Optional manifest.json to validate before tuning")
    parser.add_argument("--artifact-dir", type=Path, help="Directory for model.joblib and metadata.json")
    parser.add_argument("--no-save-artifact", action="store_true", help="Tune without writing a local artifact")
    args = parser.parse_args(argv)
    try:
        result = run_tuning(args.data_dir, args.manifest, args.artifact_dir, not args.no_save_artifact)
    except Exception as exc:
        print(f"Tuning failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(format_tuning_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

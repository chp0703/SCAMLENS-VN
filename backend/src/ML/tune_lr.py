"""Tune Logistic Regression on the shared predefined ML cross-validation folds.

The test split is deliberately excluded from this module.  GridSearchCV fits
the TF-IDF pipeline only on each CV training fold, then refits the F1-selected
estimator on the complete shared ML training pool for local artifact storage.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import json
from pathlib import Path
import sys
import tempfile
import time
import warnings

import joblib
import numpy as np
from sklearn.model_selection import GridSearchCV, ParameterGrid

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ML.data_utils import MLData, load_ml_data
from src.ML.experiment_reporting import new_run_context, source_fingerprints, versions, write_report
from src.ML.metrics import METRIC_LABELS, METRICS, SCORER_DEFINITIONS, SCORING
from src.ML.models.logistic_regression import build_lr_pipeline


PARAM_GRID = {
    "model__C": [0.01, 0.1, 1, 10, 100],
    "model__class_weight": [None, "balanced"],
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
    run_id: str | None = None,
    report_paths: dict[str, str] | None = None,
) -> ArtifactResult:
    """Persist the refitted best estimator plus safe, reproducible metadata."""
    directory = (Path(artifact_dir) if artifact_dir is not None else _default_artifact_dir()).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    model_path = directory / "model.joblib"
    metadata_path = directory / "metadata.json"
    # Stage both files then atomically replace their current versions only after
    # serialization and the reload smoke check succeed.
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".joblib", delete=False) as stream:
        staged_model = Path(stream.name)
    try:
        joblib.dump(result.best_estimator, staged_model)
        reloaded_model = joblib.load(staged_model)
    except Exception:
        staged_model.unlink(missing_ok=True)
        raise
    smoke_predictions = tuple(int(value) for value in reloaded_model.predict(["xin chao", "nhan thuong gap"]))
    metadata = {
        "model_name": "Logistic Regression TF-IDF Pipeline",
        "pipeline_components": list(result.best_estimator.named_steps),
        "best_hyperparameters": result.best_params,
        "selection_metric": "f1_scam",
        "scoring": SCORER_DEFINITIONS,
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
        "versions": versions(),
        "source_sha256": source_fingerprints or {},
        "run_id": run_id,
        "report_paths": report_paths or {},
    }
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".json", delete=False, mode="w", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        staged_metadata = Path(stream.name)
    try:
        staged_model.replace(model_path)
        staged_metadata.replace(metadata_path)
    except Exception:
        staged_model.unlink(missing_ok=True)
        staged_metadata.unlink(missing_ok=True)
        raise
    return ArtifactResult(model_path, metadata_path, smoke_predictions)


def run_tuning(
    data_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
    save_artifact: bool = True,
    report_dir: str | Path | None = None,
) -> TuningResult:
    """Load, tune, save the selected artifact, and persist a complete report."""
    context = new_run_context("tuning", report_dir)
    started = time.perf_counter()
    try:
        data = load_ml_data(data_dir=data_dir, manifest_path=manifest_path)
        result = tune_data(data)
        report_paths = {
            "markdown": f"backend/experiments/logistic_regression/runs/{context['run_id']}.md",
            "json": f"backend/experiments/logistic_regression/runs/{context['run_id']}.json",
        }
        if save_artifact:
            artifact = save_best_artifact(result, data, artifact_dir, source_fingerprints(data_dir, _default_data_dir()), context["run_id"], report_paths)
            result = replace(result, artifact=artifact)
        candidates = []
        for index, params in enumerate(result.search.cv_results_["params"]):
            candidates.append({"index": index, "params": params, "metrics": {metric: {"per_fold": [float(result.search.cv_results_[f"split{fold}_test_{metric}"][index]) for fold in result.fold_ids], "mean": float(result.search.cv_results_[f"mean_test_{metric}"][index]), "population_std": float(result.search.cv_results_[f"std_test_{metric}"][index])} for metric in METRICS}})
        write_report(context, {"status": "success", "elapsed_seconds": time.perf_counter() - started, "source_sha256": source_fingerprints(data_dir, _default_data_dir()), "training_samples": len(data.X_train), "cv_fold_ids": list(result.fold_ids), "cv_type": "PredefinedSplit", "parameter_grid": PARAM_GRID, "scoring": SCORER_DEFINITIONS, "selection_metric": "f1_scam", "candidate_count": result.candidate_count, "cv_fit_count": result.cv_fit_count, "candidates": candidates, "best_parameters": result.best_params, "selected_cv_metrics": {metric: {"per_fold": list(result.per_fold_scores[metric]), "mean": result.means[metric], "population_std": result.standard_deviations[metric]} for metric in METRICS}, "warnings": list(result.warnings), "versions": versions(), "random_seed": "not applicable (default LogisticRegression configuration)", "model_configuration": {"tfidf": build_lr_pipeline().named_steps["tfidf"].get_params(), "logistic_regression": build_lr_pipeline().named_steps["model"].get_params()}, "artifact": {"model_path": str(result.artifact.model_path), "metadata_path": str(result.artifact.metadata_path), "smoke_predictions": list(result.artifact.smoke_predictions)} if result.artifact else None})
        return result
    except Exception as exc:
        write_report(context, {"status": "failure", "elapsed_seconds": time.perf_counter() - started, "error": f"{type(exc).__name__}: {exc}", "versions": versions()})
        raise


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

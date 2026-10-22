"""Tune Logistic Regression with the shared config, CV, and artifact services."""

import argparse
from dataclasses import replace
from pathlib import Path
import sys
import time

from sklearn.model_selection import GridSearchCV

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ML.artifacts import ArtifactResult, save_artifact as publish_artifact
from src.ML.config import ModelConfig, load_model_config
from src.ML.cv import TuningResult, metric_summary, tune_data as tune_cv, tuning_summary
from src.ML.data_utils import MLData, load_ml_data
from src.ML.experiment_reporting import (
    new_run_context, pipeline_configuration, report_paths, run_payload,
    source_fingerprints, versions, write_failure_report, write_report,
)
from src.ML.metrics import METRIC_LABELS, METRICS, SCORER_DEFINITIONS, SCORING


PARAM_GRID = load_model_config("logistic_regression").param_grid
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data/splits/ml"
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "artifacts/logistic_regression"


def tune_data(data: MLData, config: ModelConfig | None = None) -> TuningResult:
    config = config or load_model_config("logistic_regression")
    return tune_cv(data, config.build_pipeline(), config.param_grid, config.primary_metric,
                   search_factory=GridSearchCV)


def save_best_artifact(result: TuningResult, data: MLData, artifact_dir=None,
                       source_fingerprints=None, run_id=None, report_paths=None) -> ArtifactResult:
    pipeline = result.best_estimator
    metadata = {
        "model_name": "Logistic Regression TF-IDF Pipeline",
        "pipeline_components": list(pipeline.named_steps),
        "best_hyperparameters": result.best_params,
        "selection_metric": result.selection_metric, "scoring": SCORER_DEFINITIONS,
        "parameter_grid": result.param_grid, "selected_cv_metrics": metric_summary(result),
        "candidate_count": result.candidate_count, "cv_fit_count": result.cv_fit_count,
        "training_samples": len(data.X_train),
        "cv": {"type": "PredefinedSplit", "fold_ids": list(result.fold_ids), "shared_fold_assignments": True},
        "label_mapping": {"0": "Ham", "1": "Scam"}, "versions": versions(),
        "source_sha256": source_fingerprints or {}, "run_id": run_id,
        "report_paths": report_paths or {}, "model_configuration": pipeline_configuration(pipeline),
        "random_seed": pipeline.named_steps["model"].get_params().get("random_state"),
    }
    return publish_artifact(pipeline, metadata,
                            artifact_dir if artifact_dir is not None else DEFAULT_ARTIFACT_DIR, run_id)


def run_tuning(data_dir=None, manifest_path=None, artifact_dir=None, save_artifact=True,
               report_dir=None, config_path=None) -> TuningResult:
    context = new_run_context("tuning", report_dir)
    started = time.perf_counter()
    try:
        config = load_model_config("logistic_regression", config_path)
        data = load_ml_data(data_dir=data_dir, manifest_path=manifest_path)
        result = tune_data(data, config)
        fingerprints = source_fingerprints(data_dir, DEFAULT_DATA_DIR)
        if save_artifact:
            artifact = save_best_artifact(result, data, artifact_dir, fingerprints,
                                          context["run_id"], report_paths(context))
            result = replace(result, artifact=artifact)
        payload = run_payload(data, result, result.best_estimator, fingerprints, started)
        artifact_payload = None if result.artifact is None else {
            "model_path": str(result.artifact.model_path),
            "metadata_path": str(result.artifact.metadata_path),
            "smoke_predictions": list(result.artifact.smoke_predictions),
        }
        write_report(context, {**payload, **tuning_summary(result), "artifact": artifact_payload})
        return result
    except Exception as exc:
        write_failure_report(context, started, exc)
        raise


def format_tuning_result(result: TuningResult) -> str:
    lines = [
        f"Logistic Regression tuning: {result.candidate_count} candidates, {result.cv_fit_count} predefined CV fits",
        f"Best parameters (selected by {result.selection_metric}): {result.best_params}",
    ]
    for index, params in enumerate(result.search.cv_results_["params"]):
        metrics = ", ".join(
            f"{METRIC_LABELS[metric]}={result.search.cv_results_[f'mean_test_{metric}'][index]:.4f}"
            for metric in METRICS
        )
        lines.append(f"  Candidate {index}: {params}; {metrics}")
    for index, fold in enumerate(result.fold_ids):
        metrics = ", ".join(f"{METRIC_LABELS[metric]}={result.per_fold_scores[metric][index]:.4f}" for metric in METRICS)
        lines.append(f"Best candidate fold {fold}: {metrics}")
    for metric in METRICS:
        lines.append(f"  {METRIC_LABELS[metric]}: {result.means[metric]:.4f} +/- {result.standard_deviations[metric]:.4f}")
    lines.extend(f"  Warning: {warning}" for warning in result.warnings)
    if result.artifact:
        lines.extend([f"Saved model: {result.artifact.model_path}",
                      f"Saved metadata: {result.artifact.metadata_path}",
                      f"Reload smoke predictions: {list(result.artifact.smoke_predictions)}"])
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--no-save-artifact", action="store_true")
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_tuning(args.data_dir, args.manifest, args.artifact_dir,
                            not args.no_save_artifact, args.report_dir, args.config)
    except Exception as exc:
        print(f"Tuning failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(format_tuning_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

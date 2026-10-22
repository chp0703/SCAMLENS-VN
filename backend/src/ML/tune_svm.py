"""Tune Linear SVM with the shared config, CV, and artifact services."""

import argparse
from pathlib import Path
import sys
import time

from sklearn.model_selection import GridSearchCV

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ML.artifacts import save_artifact as publish_artifact
from src.ML.config import ModelConfig, load_model_config
from src.ML.cv import TuningResult, metric_summary, tune_data as tune_cv, tuning_summary
from src.ML.data_utils import MLData, load_ml_data
from src.ML.experiment_reporting import (
    new_run_context, pipeline_configuration, report_paths, run_payload,
    source_fingerprints, versions, write_failure_report, write_report,
)
from src.ML.metrics import METRICS, SCORER_DEFINITIONS


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data/splits/ml"
CONFIG_PATH = BACKEND_DIR / "src/ML/configs/svm.yaml"
ARTIFACT_DIR = BACKEND_DIR / "artifacts/svm"


def load_param_grid(config_path=None) -> dict:
    return load_model_config("svm", config_path if config_path is not None else CONFIG_PATH).param_grid


def tune_data(data: MLData, config: ModelConfig | None = None) -> TuningResult:
    config = config or load_model_config("svm")
    return tune_cv(data, config.build_pipeline(), config.param_grid, config.primary_metric,
                   search_factory=GridSearchCV)


def save_best_model(estimator, metadata: dict, output_dir: Path) -> tuple[Path, Path]:
    artifact = publish_artifact(estimator, metadata, output_dir)
    return artifact.model_path, artifact.metadata_path


def run_tuning(data_dir=None, manifest_path=None, report_dir=None, artifact_dir=None,
               save_artifact=True, config_path=None):
    context = new_run_context("tuning", report_dir, model_key="svm", model_name="Support Vector Machine")
    started = time.perf_counter()
    try:
        config = load_model_config("svm", config_path if config_path is not None else CONFIG_PATH)
        data = load_ml_data(data_dir=data_dir, manifest_path=manifest_path)
        result = tune_data(data, config)
        fingerprints = source_fingerprints(data_dir, DATA_DIR)
        metadata = {
            "model_name": "LinearSVC TF-IDF Pipeline", "best_hyperparameters": result.best_params,
            "selection_metric": result.selection_metric, "selected_cv_metrics": metric_summary(result),
            "parameter_grid": result.param_grid, "scoring": SCORER_DEFINITIONS,
            "cv_type": "PredefinedSplit", "cv_fold_ids": list(result.fold_ids),
            "training_samples": len(data.X_train), "candidate_count": result.candidate_count,
            "cv_fit_count": result.cv_fit_count, "label_mapping": {"0": "Ham", "1": "Scam"},
            "source_sha256": fingerprints, "run_id": context["run_id"], "versions": versions(),
            "report_paths": report_paths(context),
            "model_configuration": pipeline_configuration(result.best_estimator),
            "random_seed": result.best_estimator.named_steps["model"].random_state,
        }
        artifact_payload = None
        if save_artifact:
            paths = save_best_model(result.best_estimator, metadata,
                                    Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR)
            artifact_payload = {"model": str(paths[0]), "metadata": str(paths[1])}
        payload = run_payload(data, result, result.best_estimator, fingerprints, started)
        write_report(context, {**payload, **tuning_summary(result), "artifact": artifact_payload})
        return result.search
    except Exception as exc:
        write_failure_report(context, started, exc)
        raise


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
        search = run_tuning(data_dir=args.data_dir, manifest_path=args.manifest,
                            report_dir=args.report_dir, artifact_dir=args.artifact_dir,
                            save_artifact=not args.no_save_artifact, config_path=args.config)
    except Exception as exc:
        print(f"SVM tuning failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"SVM tuning: {len(search.cv_results_['params'])} candidates")
    print(f"Best parameters: {search.best_params_}")
    print(f"Best CV {search.refit}: {search.best_score_:.4f}")
    for metric in METRICS:
        index = search.best_index_
        print(f"  {metric}: {search.cv_results_[f'mean_test_{metric}'][index]:.4f}"
              f" +/- {search.cv_results_[f'std_test_{metric}'][index]:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

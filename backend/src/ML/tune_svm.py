
"""Tune Linear SVM on shared predefined CV folds.

The held-out Test Set is never used for tuning.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile
import time
import warnings

import joblib
import yaml
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import GridSearchCV, ParameterGrid

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ML.data_utils import load_ml_data
from src.ML.experiment_reporting import (
    new_run_context,
    source_fingerprints,
    versions,
)
from src.ML.metrics import METRICS, SCORING, SCORER_DEFINITIONS
from src.ML.models.svm import build_svm_pipeline
from src.ML.train_svm import write_svm_report


BACKEND_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BACKEND_DIR / "data" / "splits" / "ml"
CONFIG_PATH = BACKEND_DIR / "src" / "ML" / "configs" / "svm.yaml"
REPORT_DIR = BACKEND_DIR / "experiments" / "svm" / "runs"
ARTIFACT_DIR = BACKEND_DIR / "artifacts" / "svm"


def load_param_grid() -> dict:
    """Read SVM search space from YAML."""
    with CONFIG_PATH.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

    if not isinstance(config, dict):
        raise ValueError("Invalid SVM configuration")

    tuning = config.get("tuning")
    if not isinstance(tuning, dict):
        raise ValueError("Missing tuning configuration")

    grid = {
        "model__C": tuning["model__C"],
        "model__class_weight": tuning["model__class_weight"],
    }

    if not grid["model__C"] or not grid["model__class_weight"]:
        raise ValueError("Hyperparameter lists cannot be empty")

    return grid


def save_best_model(
    estimator,
    metadata: dict,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Save and reload the selected model before publishing it."""
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "model.joblib"
    metadata_path = output_dir / "metadata.json"

    with tempfile.NamedTemporaryFile(
        dir=output_dir,
        suffix=".joblib",
        delete=False,
    ) as stream:
        staged_path = Path(stream.name)

    try:
        joblib.dump(estimator, staged_path)

        reloaded = joblib.load(staged_path)
        predictions = reloaded.predict([
            "xin chao",
            "nhan thuong gap",
        ])

        metadata["smoke_predictions"] = [
            int(value) for value in predictions
        ]

        # Existing artifact is updated only after reload succeeds.
        staged_path.replace(model_path)

        import json

        metadata_path.write_text(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            ) + "\n",
            encoding="utf-8",
        )

    finally:
        staged_path.unlink(missing_ok=True)

    return model_path, metadata_path


def run_tuning(
    data_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
    report_dir: str | Path | None = None,
    artifact_dir: str | Path | None = None,
    save_artifact: bool = True,
):
    """Tune SVM using the same training pool and CV folds as LR."""
    context = new_run_context(
        "tuning",
        report_dir if report_dir is not None else REPORT_DIR,
    )

    started = time.perf_counter()

    try:
        data = load_ml_data(
            data_dir=data_dir,
            manifest_path=manifest_path,
        )

        param_grid = load_param_grid()

        search = GridSearchCV(
            estimator=build_svm_pipeline(),
            param_grid=param_grid,
            scoring=SCORING,
            refit="f1_scam",
            cv=data.cv,
            n_jobs=1,
            error_score="raise",
            return_train_score=False,
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            search.fit(data.X_train, data.y_train)

        results = search.cv_results_
        best_index = int(search.best_index_)
        fold_ids = sorted(set(int(fold) for fold in data.fold_ids))

        selected_metrics = {
            metric: {
                "mean": float(
                    results[f"mean_test_{metric}"][best_index]
                ),
                "population_std": float(
                    results[f"std_test_{metric}"][best_index]
                ),
                "per_fold": [
                    float(
                        results[
                            f"split{fold}_test_{metric}"
                        ][best_index]
                    )
                    for fold in fold_ids
                ],
            }
            for metric in METRICS
        }

        candidates = [
            {
                "params": params,
                "metrics": {
                    metric: {
                        "mean": float(
                            results[f"mean_test_{metric}"][i]
                        ),
                        "population_std": float(
                            results[f"std_test_{metric}"][i]
                        ),
                    }
                    for metric in METRICS
                },
            }
            for i, params in enumerate(results["params"])
        ]

        warning_messages = [
            f"{w.category.__name__}: {w.message}"
            for w in caught
            if issubclass(w.category, ConvergenceWarning)
        ]

        fingerprints = source_fingerprints(
            data_dir, DATA_DIR
        )

        metadata = {
            "model_name": "LinearSVC TF-IDF Pipeline",
            "best_hyperparameters": search.best_params_,
            "selection_metric": "f1_scam",
            "selected_cv_metrics": selected_metrics,
            "parameter_grid": param_grid,
            "scoring": SCORER_DEFINITIONS,
            "cv_type": "PredefinedSplit",
            "cv_fold_ids": fold_ids,
            "training_samples": len(data.X_train),
            "candidate_count": len(results["params"]),
            "cv_fit_count": len(results["params"]) * len(fold_ids),
            "label_mapping": {"0": "Ham", "1": "Scam"},
            "source_sha256": fingerprints,
            "run_id": context["run_id"],
            "versions": versions(),
        }

        artifact_paths = None

        if save_artifact:
            output_dir = Path(
                artifact_dir if artifact_dir is not None
                else ARTIFACT_DIR
            ).resolve()

            model_path, metadata_path = save_best_model(
                search.best_estimator_,
                metadata,
                output_dir,
            )

            artifact_paths = {
                "model": str(model_path),
                "metadata": str(metadata_path),
            }

        payload = {
            "status": "success",
            "model": "LinearSVC",
            "elapsed_seconds": time.perf_counter() - started,
            "training_samples": len(data.X_train),
            "source_sha256": fingerprints,
            "cv_type": "PredefinedSplit",
            "cv_fold_ids": fold_ids,
            "parameter_grid": param_grid,
            "scoring": SCORER_DEFINITIONS,
            "selection_metric": "f1_scam",
            "best_parameters": search.best_params_,
            "selected_cv_metrics": selected_metrics,
            "candidate_count": metadata["candidate_count"],
            "cv_fit_count": metadata["cv_fit_count"],
            "candidates": candidates,
            "warnings": warning_messages,
            "artifact": artifact_paths,
            "versions": versions(),
            "random_seed": 42,
        }

        write_svm_report(context, payload)
        return search

    except Exception as exc:
        write_svm_report(context, {
            "status": "failure",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": time.perf_counter() - started,
            "versions": versions(),
        })
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument(
        "--no-save-artifact",
        action="store_true",
    )

    args = parser.parse_args()

    try:
        search = run_tuning(
            data_dir=args.data_dir,
            manifest_path=args.manifest,
            artifact_dir=args.artifact_dir,
            save_artifact=not args.no_save_artifact,
        )
    except Exception as exc:
        print(
            f"SVM tuning failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    print("\nSVM Tuning Completed")
    print(f"Candidates: {len(ParameterGrid(load_param_grid()))}")
    print(f"Best parameters: {search.best_params_}")
    print(f"Best CV F1 Scam: {search.best_score_:.4f}")

    print("\nSelected CV metrics:")
    for metric in METRICS:
        index = search.best_index_
        mean = search.cv_results_[f"mean_test_{metric}"][index]
        std = search.cv_results_[f"std_test_{metric}"][index]
        print(f"  {metric}: {mean:.4f} +/- {std:.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


"""Reproducible cross-validation baseline for Linear SVM."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import time
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import cross_validate

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ML.data_utils import MLData, load_ml_data
from src.ML.experiment_reporting import (
    new_run_context,
    source_fingerprints,
    versions,
    write_report,
)
from src.ML.metrics import METRIC_LABELS, SCORING
from src.ML.models.svm import build_svm_pipeline


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_DIR / "data" / "splits" / "ml"
DEFAULT_REPORT_DIR = (
    BACKEND_DIR / "experiments" / "svm" / "runs"
)


@dataclass(frozen=True)
class BaselineResult:
    fold_ids: tuple[int, ...]
    scores: dict[str, tuple[float, ...]]
    means: dict[str, float]
    standard_deviations: dict[str, float]
    warnings: tuple[str, ...]


def evaluate_baseline(data: MLData) -> BaselineResult:
    """Run CV without using the held-out Test Set."""
    pipeline = build_svm_pipeline()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        raw = cross_validate(
            pipeline,
            data.X_train,
            data.y_train,
            cv=data.cv,
            scoring=SCORING,
            error_score="raise",
            return_train_score=False,
        )

    fold_ids = tuple(sorted(set(map(int, data.fold_ids))))
    scores = {
        metric: tuple(map(float, raw[f"test_{metric}"]))
        for metric in SCORING
    }

    if any(len(values) != len(fold_ids) for values in scores.values()):
        raise RuntimeError("Unexpected number of CV folds")

    warning_messages = tuple(
        f"{w.category.__name__}: {w.message}"
        for w in caught
        if issubclass(w.category, ConvergenceWarning)
    )

    return BaselineResult(
        fold_ids=fold_ids,
        scores=scores,
        means={
            key: float(np.mean(values))
            for key, values in scores.items()
        },
        standard_deviations={
            key: float(np.std(values, ddof=0))
            for key, values in scores.items()
        },
        warnings=warning_messages,
    )


def write_svm_report(context: dict, payload: dict) -> None:
    """Use team reporting utilities with the correct SVM title."""
    md_path, _ = write_report(context, payload)
    content = md_path.read_text(encoding="utf-8")
    content = content.replace(
        "# Logistic Regression ",
        "# Support Vector Machine ",
        1,
    )
    md_path.write_text(content, encoding="utf-8")


def run_baseline(
    data_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> BaselineResult:
    context = new_run_context(
        "baseline",
        report_dir or DEFAULT_REPORT_DIR,
    )
    started = time.perf_counter()

    try:
        data = load_ml_data(
            data_dir=data_dir,
            manifest_path=manifest_path,
        )
        result = evaluate_baseline(data)
        pipeline = build_svm_pipeline()

        payload = {
            "status": "success",
            "model": "LinearSVC",
            "elapsed_seconds": time.perf_counter() - started,
            "source_sha256": source_fingerprints(
                data_dir, DEFAULT_DATA_DIR
            ),
            "training_samples": len(data.X_train),
            "cv_type": "PredefinedSplit",
            "cv_fold_ids": list(result.fold_ids),
            "scoring": {
                key: METRIC_LABELS[key]
                for key in SCORING
            },
            "metrics": {
                key: {
                    "per_fold": list(result.scores[key]),
                    "mean": result.means[key],
                    "population_std": result.standard_deviations[key],
                }
                for key in SCORING
            },
            "warnings": list(result.warnings),
            "model_configuration": pipeline.get_params(),
            "versions": versions(),
            "random_seed": 42,
        }

        write_svm_report(context, payload)
        return result

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
    args = parser.parse_args()

    try:
        result = run_baseline(args.data_dir, args.manifest)
    except Exception as exc:
        print(f"SVM baseline failed: {exc}", file=sys.stderr)
        return 1

    print("SVM Baseline - Cross Validation")
    for metric in SCORING:
        print(
            f"{METRIC_LABELS[metric]}: "
            f"{result.means[metric]:.4f} +/- "
            f"{result.standard_deviations[metric]:.4f}"
        )
    if result.warnings:
        print("Convergence warnings:")
        print("\n".join(result.warnings))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

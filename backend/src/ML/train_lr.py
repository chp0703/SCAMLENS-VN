"""Reproducible cross-validation baseline for Logistic Regression.

This entrypoint evaluates only the shared ML training pool. ``test.csv`` is
loaded for split validation but is never passed to the estimator or a scorer.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import f1_score, make_scorer, precision_score, recall_score
from sklearn.model_selection import cross_validate

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ML.data_utils import MLData, load_ml_data
from src.ML.models.logistic_regression import build_lr_pipeline


SCORING = {
    "f1_scam": make_scorer(f1_score, pos_label=1, zero_division=0),
    "precision_scam": make_scorer(precision_score, pos_label=1, zero_division=0),
    "recall_scam": make_scorer(recall_score, pos_label=1, zero_division=0),
}
METRIC_LABELS = {
    "f1_scam": "F1 (Scam, pos_label=1)",
    "precision_scam": "Precision (Scam, pos_label=1)",
    "recall_scam": "Recall (Scam, pos_label=1)",
}


@dataclass(frozen=True)
class BaselineResult:
    """Per-fold scores, aggregate scores, and captured evaluation warnings."""

    fold_ids: tuple[int, ...]
    scores: dict[str, tuple[float, ...]]
    means: dict[str, float]
    standard_deviations: dict[str, float]
    warnings: tuple[str, ...]


def evaluate_baseline(data: MLData) -> BaselineResult:
    """Evaluate the default LR pipeline with ``data.cv`` and Scam-only metrics.

    The sklearn pipeline is cloned and fit by ``cross_validate`` inside each
    predefined training fold, so TF-IDF never learns from validation samples.
    ``X_test`` and ``y_test`` are intentionally not referenced.
    """
    pipeline = build_lr_pipeline()
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        raw_scores = cross_validate(
            pipeline,
            data.X_train,
            data.y_train,
            cv=data.cv,
            scoring=SCORING,
            error_score="raise",
            return_train_score=False,
        )

    fold_ids = tuple(sorted({int(fold) for fold in data.fold_ids}))
    scores = {
        metric: tuple(float(value) for value in raw_scores[f"test_{metric}"])
        for metric in SCORING
    }
    if any(len(values) != len(fold_ids) for values in scores.values()):
        raise RuntimeError("PredefinedSplit produced an unexpected number of score rows")
    warning_messages = tuple(
        f"{warning.category.__name__}: {warning.message}"
        for warning in caught_warnings
        if issubclass(warning.category, ConvergenceWarning)
    )
    return BaselineResult(
        fold_ids=fold_ids,
        scores=scores,
        means={metric: float(np.mean(values)) for metric, values in scores.items()},
        standard_deviations={metric: float(np.std(values, ddof=0)) for metric, values in scores.items()},
        warnings=warning_messages,
    )


def run_baseline(
    data_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
) -> BaselineResult:
    """Load validated shared data and evaluate the fixed default LR baseline."""
    return evaluate_baseline(load_ml_data(data_dir=data_dir, manifest_path=manifest_path))


def format_baseline_result(result: BaselineResult) -> str:
    """Return a readable, unambiguous console summary."""
    lines = [f"Logistic Regression baseline: {len(result.fold_ids)} predefined CV folds"]
    for index, fold_id in enumerate(result.fold_ids):
        metrics = ", ".join(
            f"{METRIC_LABELS[metric]}={result.scores[metric][index]:.4f}"
            for metric in SCORING
        )
        lines.append(f"Fold {fold_id}: {metrics}")
    lines.append("Aggregate (mean +/- population std across folds):")
    for metric in SCORING:
        lines.append(
            f"  {METRIC_LABELS[metric]}: "
            f"{result.means[metric]:.4f} +/- {result.standard_deviations[metric]:.4f}"
        )
    if result.warnings:
        lines.append("Convergence warnings:")
        lines.extend(f"  {warning}" for warning in result.warnings)
    else:
        lines.append("Convergence warnings: none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="Directory containing ML train.csv, test.csv, and cv_folds.csv")
    parser.add_argument("--manifest", type=Path, help="Optional manifest.json to validate before evaluation")
    args = parser.parse_args(argv)
    try:
        result = run_baseline(args.data_dir, args.manifest)
    except Exception as exc:  # CLI should expose evaluation failures clearly.
        print(f"Baseline evaluation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(format_baseline_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Percentile and paired bootstrap confidence intervals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .metrics import METRIC_NAMES, metric_value, score_predictions


DEFAULT_BOOTSTRAP_REPLICATES = 2_000
DEFAULT_CONFIDENCE_LEVEL = 0.95
DEFAULT_RANDOM_SEED = 42


@dataclass(frozen=True)
class BootstrapInterval:
    estimate: float
    lower: float
    upper: float
    replicates: int
    confidence_level: float


@dataclass(frozen=True)
class PairedBootstrapDifference:
    metric: str
    model_a_estimate: float
    model_b_estimate: float
    difference_estimate: float
    lower: float
    upper: float
    replicates: int
    confidence_level: float


def _validate_options(n_bootstrap: int, confidence_level: float) -> None:
    if n_bootstrap < 2:
        raise ValueError("n_bootstrap must be at least 2")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1")


def _validate_inputs(y_true, y_pred) -> tuple[np.ndarray, np.ndarray]:
    result = score_predictions(y_true, y_pred)
    actual = np.asarray(y_true)
    predicted = np.asarray(y_pred)
    if result.sample_count != len(predicted):
        raise ValueError("y_true and y_pred must have the same length")
    return actual, predicted


def _interval(values: np.ndarray, estimate: float, n_bootstrap: int, confidence_level: float) -> BootstrapInterval:
    alpha = (1 - confidence_level) * 100
    return BootstrapInterval(
        estimate=float(estimate),
        lower=float(np.percentile(values, alpha / 2)),
        upper=float(np.percentile(values, 100 - alpha / 2)),
        replicates=n_bootstrap,
        confidence_level=confidence_level,
    )


def _indices(n_samples: int, n_bootstrap: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n_samples, size=(n_bootstrap, n_samples))


def bootstrap_metric_intervals(
    y_true: Sequence[int],
    y_pred: Sequence[int],
    *,
    n_bootstrap: int = DEFAULT_BOOTSTRAP_REPLICATES,
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    seed: int = DEFAULT_RANDOM_SEED,
) -> dict[str, BootstrapInterval]:
    """Calculate percentile bootstrap intervals for all required metrics."""
    _validate_options(n_bootstrap, confidence_level)
    actual, predicted = _validate_inputs(y_true, y_pred)
    point = score_predictions(actual, predicted)
    distributions = {name: np.empty(n_bootstrap, dtype=float) for name in METRIC_NAMES}
    for row, sample_indices in enumerate(_indices(len(actual), n_bootstrap, seed)):
        sampled = score_predictions(actual[sample_indices], predicted[sample_indices])
        for name in METRIC_NAMES:
            distributions[name][row] = metric_value(sampled, name)
    return {
        name: _interval(distributions[name], metric_value(point, name), n_bootstrap, confidence_level)
        for name in METRIC_NAMES
    }


def paired_bootstrap_metric_differences(
    y_true: Sequence[int],
    y_pred_a: Sequence[int],
    y_pred_b: Sequence[int],
    *,
    n_bootstrap: int = DEFAULT_BOOTSTRAP_REPLICATES,
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    seed: int = DEFAULT_RANDOM_SEED,
) -> dict[str, PairedBootstrapDifference]:
    """Compare two models using the same bootstrap indices per replicate."""
    _validate_options(n_bootstrap, confidence_level)
    actual, predicted_a = _validate_inputs(y_true, y_pred_a)
    _, predicted_b = _validate_inputs(y_true, y_pred_b)
    point_a = score_predictions(actual, predicted_a)
    point_b = score_predictions(actual, predicted_b)
    distributions = {name: np.empty(n_bootstrap, dtype=float) for name in METRIC_NAMES}
    alpha = (1 - confidence_level) * 100
    for row, sample_indices in enumerate(_indices(len(actual), n_bootstrap, seed)):
        sampled_a = score_predictions(actual[sample_indices], predicted_a[sample_indices])
        sampled_b = score_predictions(actual[sample_indices], predicted_b[sample_indices])
        for name in METRIC_NAMES:
            distributions[name][row] = metric_value(sampled_a, name) - metric_value(sampled_b, name)
    return {
        name: PairedBootstrapDifference(
            metric=name,
            model_a_estimate=metric_value(point_a, name),
            model_b_estimate=metric_value(point_b, name),
            difference_estimate=metric_value(point_a, name) - metric_value(point_b, name),
            lower=float(np.percentile(distributions[name], alpha / 2)),
            upper=float(np.percentile(distributions[name], 100 - alpha / 2)),
            replicates=n_bootstrap,
            confidence_level=confidence_level,
        )
        for name in METRIC_NAMES
    }

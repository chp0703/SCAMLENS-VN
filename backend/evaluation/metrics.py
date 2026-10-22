"""Metrics for final binary Scam/Ham model evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


POS_LABEL = 1
NEG_LABEL = 0

METRIC_NAMES = (
    "accuracy",
    "precision_scam",
    "recall_scam",
    "f1_scam",
)


@dataclass(frozen=True)
class ConfusionCounts:
    """Counts in TN, FP, FN, TP order for labels 0 and 1."""

    tn: int
    fp: int
    fn: int
    tp: int


@dataclass(frozen=True)
class MetricValues:
    accuracy: float
    precision_scam: float
    recall_scam: float
    f1_scam: float


@dataclass(frozen=True)
class EvaluationMetrics:
    sample_count: int
    values: MetricValues
    confusion: ConfusionCounts


def _validate_labels(y_true: Sequence[int], y_pred: Sequence[int]) -> tuple[np.ndarray, np.ndarray]:
    actual = np.asarray(y_true)
    predicted = np.asarray(y_pred)
    if actual.ndim != 1 or predicted.ndim != 1:
        raise ValueError("y_true and y_pred must be one-dimensional")
    if len(actual) == 0:
        raise ValueError("y_true and y_pred must not be empty")
    if len(actual) != len(predicted):
        raise ValueError("y_true and y_pred must have the same length")
    for name, values in (("y_true", actual), ("y_pred", predicted)):
        if not set(values.tolist()).issubset({NEG_LABEL, POS_LABEL}):
            raise ValueError(f"{name} must contain only labels 0 and 1")
    return actual, predicted


def confusion_counts(y_true: Sequence[int], y_pred: Sequence[int]) -> ConfusionCounts:
    actual, predicted = _validate_labels(y_true, y_pred)
    matrix = confusion_matrix(actual, predicted, labels=[NEG_LABEL, POS_LABEL])
    tn, fp, fn, tp = matrix.ravel()
    return ConfusionCounts(int(tn), int(fp), int(fn), int(tp))


def score_predictions(y_true: Sequence[int], y_pred: Sequence[int]) -> EvaluationMetrics:
    actual, predicted = _validate_labels(y_true, y_pred)
    return EvaluationMetrics(
        sample_count=len(actual),
        values=MetricValues(
            accuracy=float(accuracy_score(actual, predicted)),
            precision_scam=float(
                precision_score(actual, predicted, average="binary", pos_label=POS_LABEL, zero_division=0)
            ),
            recall_scam=float(
                recall_score(actual, predicted, average="binary", pos_label=POS_LABEL, zero_division=0)
            ),
            f1_scam=float(
                f1_score(actual, predicted, average="binary", pos_label=POS_LABEL, zero_division=0)
            ),
        ),
        confusion=confusion_counts(actual, predicted),
    )


def metric_value(result: EvaluationMetrics, name: str) -> float:
    if name not in METRIC_NAMES:
        raise ValueError(f"Unknown metric: {name}")
    return float(getattr(result.values, name))

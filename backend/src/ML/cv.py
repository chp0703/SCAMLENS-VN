"""Shared predefined CV evaluation, tuning, and result serialization."""

from dataclasses import dataclass
import warnings

import numpy as np
from sklearn.model_selection import GridSearchCV, cross_validate

from src.ML.artifacts import ArtifactResult
from src.ML.data_utils import MLData
from src.ML.metrics import METRICS, SCORING


@dataclass(frozen=True)
class BaselineResult:
    fold_ids: tuple[int, ...]
    scores: dict[str, tuple[float, ...]]
    means: dict[str, float]
    standard_deviations: dict[str, float]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class TuningResult:
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
    param_grid: dict
    selection_metric: str
    artifact: ArtifactResult | None = None

    @property
    def best_estimator(self):
        return self.search.best_estimator_


def evaluate_baseline(data: MLData, pipeline, *, cross_validate_fn=cross_validate) -> BaselineResult:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        raw = cross_validate_fn(pipeline, data.X_train, data.y_train, cv=data.cv,
                                scoring=SCORING, error_score="raise", return_train_score=False)
    folds = tuple(sorted(set(map(int, data.fold_ids))))
    scores = {metric: tuple(map(float, raw[f"test_{metric}"])) for metric in METRICS}
    if any(len(values) != len(folds) for values in scores.values()):
        raise RuntimeError("PredefinedSplit produced an unexpected number of score rows")
    return BaselineResult(
        folds, scores, {metric: float(np.mean(values)) for metric, values in scores.items()},
        {metric: float(np.std(values, ddof=0)) for metric, values in scores.items()},
        tuple(f"{warning.category.__name__}: {warning.message}" for warning in caught),
    )


def tune_data(data: MLData, pipeline, param_grid: dict, selection_metric: str,
              *, search_factory=GridSearchCV) -> TuningResult:
    if selection_metric not in SCORING:
        raise ValueError(f"Unknown selection metric: {selection_metric}")
    search = search_factory(estimator=pipeline, param_grid=param_grid, scoring=SCORING,
                            refit=selection_metric, cv=data.cv, return_train_score=False,
                            error_score="raise", n_jobs=1)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        search.fit(data.X_train, data.y_train)
    index = int(search.best_index_)
    raw = search.cv_results_
    folds = tuple(sorted(set(map(int, data.fold_ids))))
    scores = {metric: tuple(float(raw[f"split{fold}_test_{metric}"][index]) for fold in folds)
              for metric in METRICS}
    count = len(raw["params"])
    return TuningResult(
        search, dict(search.best_params_), index, folds, scores,
        {metric: float(raw[f"mean_test_{metric}"][index]) for metric in METRICS},
        {metric: float(raw[f"std_test_{metric}"][index]) for metric in METRICS}, count, count * len(folds),
        tuple(f"{warning.category.__name__}: {warning.message}" for warning in caught),
        param_grid, selection_metric,
    )


def metric_summary(result: BaselineResult | TuningResult) -> dict:
    scores = result.scores if isinstance(result, BaselineResult) else result.per_fold_scores
    return {metric: {"per_fold": list(scores[metric]), "mean": result.means[metric],
                     "population_std": result.standard_deviations[metric]} for metric in METRICS}


def tuning_summary(result: TuningResult) -> dict:
    raw = result.search.cv_results_
    return {
        "parameter_grid": result.param_grid, "selection_metric": result.selection_metric,
        "best_parameters": result.best_params, "candidate_count": result.candidate_count,
        "cv_fit_count": result.cv_fit_count, "selected_cv_metrics": metric_summary(result),
        "candidates": [
            {"index": index, "params": params, "metrics": {
                metric: {"mean": float(raw[f"mean_test_{metric}"][index]),
                         "population_std": float(raw[f"std_test_{metric}"][index]),
                         "per_fold": [float(raw[f"split{fold}_test_{metric}"][index]) for fold in result.fold_ids]}
                for metric in METRICS}}
            for index, params in enumerate(raw["params"])
        ],
    }

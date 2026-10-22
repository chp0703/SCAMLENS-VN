"""Validated configuration shared by the LR and SVM entrypoints."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.ML.metrics import SCORING
from src.ML.models.logistic_regression import build_lr_pipeline
from src.ML.models.svm import build_svm_pipeline


BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_SPECS = {
    "logistic_regression": ("lr.yaml", "LogisticRegression", "Logistic Regression", build_lr_pipeline),
    "svm": ("svm.yaml", "LinearSVC", "Support Vector Machine", build_svm_pipeline),
}


@dataclass(frozen=True)
class ModelConfig:
    model_key: str
    model_name: str
    estimator_type: str
    tfidf_params: dict[str, Any]
    model_params: dict[str, Any]
    param_grid: dict[str, list]
    primary_metric: str
    path: Path

    def build_pipeline(self):
        return MODEL_SPECS[self.model_key][3](self.tfidf_params, self.model_params)


def _mapping(value: Any, name: str, allowed: set[str] | None = None) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    if allowed is not None and value.keys() - allowed:
        raise ValueError(f"Unknown {name} settings: {sorted(value.keys() - allowed)}")
    return value


def load_model_config(model_key: str, path: str | Path | None = None) -> ModelConfig:
    if model_key not in MODEL_SPECS:
        raise ValueError(f"Unknown model: {model_key}")
    filename, estimator_type, model_name, builder = MODEL_SPECS[model_key]
    config_path = Path(path) if path is not None else Path(__file__).parent / "configs" / filename
    with config_path.open(encoding="utf-8") as stream:
        document = _mapping(yaml.safe_load(stream), "config", {"model", "tfidf", "tuning", "evaluation"})
    model = _mapping(document.get("model"), "model", {"type", "params"})
    if model.get("type") != estimator_type:
        raise ValueError(f"model.type must be {estimator_type}")
    model_params = dict(_mapping(model.get("params", {}), "model.params"))
    tfidf_params = dict(_mapping(document.get("tfidf", {}), "tfidf"))
    if isinstance(tfidf_params.get("ngram_range"), list):
        tfidf_params["ngram_range"] = tuple(tfidf_params["ngram_range"])
    evaluation = _mapping(document.get("evaluation"), "evaluation", {"primary_metric"})
    primary_metric = evaluation.get("primary_metric")
    if not isinstance(primary_metric, str) or primary_metric not in SCORING:
        raise ValueError(f"evaluation.primary_metric must be one of {tuple(SCORING)}")
    grid = _mapping(document.get("tuning"), "tuning")
    if not grid:
        raise ValueError("tuning must contain at least one parameter")
    try:
        pipeline = builder(tfidf_params, model_params)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid model/TF-IDF parameters: {exc}") from exc
    known_params = pipeline.get_params()
    param_grid = {}
    for name, values in grid.items():
        if name not in known_params or "__" not in name:
            raise ValueError(f"Unknown tuning parameter: {name}")
        if not isinstance(values, list) or not values:
            raise ValueError(f"tuning.{name} must be a nonempty list")
        if name == "tfidf__ngram_range":
            values = [tuple(value) if isinstance(value, list) else value for value in values]
        if name == "model__C" and any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0
            for value in values
        ):
            raise ValueError("tuning.model__C values must be positive numbers")
        param_grid[name] = values
    return ModelConfig(model_key, model_name, estimator_type, tfidf_params, model_params,
                       param_grid, primary_metric, config_path.resolve())

"""Load the team's pinned pipelines without consulting local training pointers."""

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform

import joblib
import numpy as np

from app.services.preprocessing import RULES_VERSION, normalize_text


DEFAULT_LOCK = Path(__file__).resolve().parents[2] / "models.lock.json"
DEFAULT_DECISION_RULE = {
    "method": "pipeline.predict", "score_type": "decision_function", "threshold": 0.0,
}


def _resolve(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Model lock paths must stay inside the backend directory")
    return path


def _verify_file(path: Path, digest: str, *, normalize_lf: bool = False) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing shared model file: {path}; run git lfs pull")
    content = path.read_bytes()
    if content.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise ValueError(f"LFS pointer has not been downloaded: {path}; run git lfs pull")
    if normalize_lf:
        content = content.replace(b"\r\n", b"\n")
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError(f"Shared model SHA-256 mismatch: {path}")


def read_model_lock(lock_path: str | Path = DEFAULT_LOCK) -> dict:
    path = Path(lock_path).resolve()
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not document.get("models"):
        raise ValueError("Invalid models.lock.json schema")
    runtime = document["runtime"]
    if ".".join(platform.python_version_tuple()[:2]) != runtime["python_series"]:
        raise RuntimeError(f"Shared models require Python {runtime['python_series']}.x")
    for package, expected in runtime["packages"].items():
        actual = version(package)
        if actual != expected:
            raise RuntimeError(
                f"Shared models require {package}=={expected}; found {actual}. "
                "Install backend/requirements-models.lock.txt in the selected environment."
            )
    preprocessing = document["preprocessing"]
    expected_path = _resolve(path.parent, preprocessing["path"])
    actual_path = Path(__file__).resolve().parents[2] / "app/services/preprocessing.py"
    if expected_path != actual_path:
        raise ValueError("Model lock must reference the shared preprocessing module")
    _verify_file(expected_path, preprocessing["sha256_lf"], normalize_lf=True)
    if preprocessing["rules_version"] != RULES_VERSION:
        raise ValueError("Shared preprocessing rules version differs from the model lock")
    return document


def load_approved_artifact(model_key: str, lock_path: str | Path = DEFAULT_LOCK):
    """Verify runtime, preprocessing and both artifact files before deserialization."""
    path = Path(lock_path).resolve()
    document = read_model_lock(path)
    if model_key not in document["models"]:
        raise ValueError(f"Unknown shared model: {model_key}")
    entry = document["models"][model_key]
    if entry["decision_rule"] != DEFAULT_DECISION_RULE:
        raise ValueError("Only the pinned default pipeline decision rule is supported")
    directory = _resolve(path.parent, entry["artifact_dir"])
    model_path, metadata_path = directory / "model.joblib", directory / "metadata.json"
    _verify_file(model_path, entry["model_sha256"])
    _verify_file(metadata_path, entry["metadata_sha256"])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata["run_id"] != entry["run_id"]:
        raise ValueError("Shared model run_id differs from the model lock")
    if metadata["source_sha256"] != document["training_source_sha256"]:
        raise ValueError("Shared model training data differs from the model lock")
    model = joblib.load(model_path)
    if list(model.named_steps) != ["tfidf", "model"] or list(model.classes_) != [0, 1]:
        raise ValueError("Shared model must be the fitted binary TF-IDF + classifier pipeline")
    return model, {
        **metadata,
        "shared_bundle_id": document["bundle_id"],
        "shared_model_key": model_key,
        "model_sha256": entry["model_sha256"],
        "decision_rule": entry["decision_rule"],
    }


def predict_approved_texts(model_key: str, texts: list[str], lock_path: str | Path = DEFAULT_LOCK) -> dict:
    """Run the pinned normalization and default classifier decision on raw text."""
    model, metadata = load_approved_artifact(model_key, lock_path)
    normalized = [normalize_text(text) for text in texts]
    return {
        "model_key": model_key,
        "bundle_id": metadata["shared_bundle_id"],
        "run_id": metadata["run_id"],
        "labels": model.predict(normalized).tolist(),
        "decision_scores": model.decision_function(normalized).tolist(),
        "score_type": "decision_function",
    }


def verify_shared_models(lock_path: str | Path = DEFAULT_LOCK) -> dict:
    """Check the shared synthetic regression cases; never read the held-out test."""
    path = Path(lock_path).resolve()
    document = read_model_lock(path)
    smoke = document["smoke_test"]
    fixture = _resolve(path.parent, smoke["path"])
    _verify_file(fixture, smoke["sha256"])
    cases = json.loads(fixture.read_text(encoding="utf-8"))
    results = {}
    for key in document["models"]:
        result = predict_approved_texts(key, cases["raw_texts"], path)
        expected = cases["models"][key]
        if result["labels"] != expected["labels"] or not np.allclose(
            result["decision_scores"], expected["decision_scores"],
            rtol=0, atol=smoke["score_absolute_tolerance"],
        ):
            raise ValueError(f"Shared model regression predictions differ: {key}")
        results[key] = {"run_id": result["run_id"], "cases_passed": len(cases["raw_texts"])}
    return {"status": "PASS", "bundle_id": document["bundle_id"], "models": results}

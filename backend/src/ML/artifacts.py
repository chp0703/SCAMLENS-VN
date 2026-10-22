"""Publish immutable model/metadata pairs through one atomic current pointer."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import tempfile
import uuid

import joblib


@dataclass(frozen=True)
class ArtifactResult:
    model_path: Path
    metadata_path: Path
    smoke_predictions: tuple[int, ...]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_run_id(run_id: str) -> None:
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("run_id must be a simple directory name")


def save_artifact(estimator, metadata: dict, output_dir: str | Path,
                  run_id: str | None = None) -> ArtifactResult:
    directory = Path(output_dir).resolve()
    version_id = run_id if run_id is not None else metadata.get("run_id") or uuid.uuid4().hex
    _validate_run_id(version_id)
    runs = directory / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    destination = runs / version_id
    if destination.exists():
        raise FileExistsError(f"Artifact run already exists: {version_id}")
    staging = Path(tempfile.mkdtemp(dir=runs, prefix=".staging-"))
    pointer_temp = None
    try:
        model_path, metadata_path = staging / "model.joblib", staging / "metadata.json"
        joblib.dump(estimator, model_path)
        reloaded = joblib.load(model_path)
        probes = ["xin chao", "nhan thuong gap"]
        predictions = tuple(int(value) for value in reloaded.predict(probes))
        if predictions != tuple(int(value) for value in estimator.predict(probes)):
            raise ValueError("Reloaded model predictions differ from the fitted model")
        document = {**metadata, "artifact_schema_version": 1, "run_id": version_id,
                    "smoke_predictions": list(predictions), "model_sha256": _sha256(model_path)}
        metadata_path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True,
                       default=str, allow_nan=False) + "\n", encoding="utf-8",
        )
        pointer = {"schema_version": 1, "run_id": version_id,
                   "model_sha256": _sha256(model_path), "metadata_sha256": _sha256(metadata_path)}
        staging.rename(destination)
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".current-", suffix=".json",
                                         mode="w", encoding="utf-8", delete=False) as stream:
            pointer_temp = Path(stream.name)
            json.dump(pointer, stream, sort_keys=True)
            stream.write("\n")
        pointer_temp.replace(directory / "current.json")
        return ArtifactResult(destination / "model.joblib", destination / "metadata.json", predictions)
    finally:
        if pointer_temp is not None:
            pointer_temp.unlink(missing_ok=True)
        if staging.exists():
            for name in ("model.joblib", "metadata.json"):
                (staging / name).unlink(missing_ok=True)
            staging.rmdir()


def resolve_artifact_paths(output_dir: str | Path) -> tuple[Path, Path]:
    directory = Path(output_dir).resolve()
    pointer_path = directory / "current.json"
    if not pointer_path.exists():
        paths = directory / "model.joblib", directory / "metadata.json"
        if not all(path.is_file() for path in paths):
            raise FileNotFoundError(f"No complete artifact in {directory}")
        return paths
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    if not isinstance(pointer, dict) or pointer.get("schema_version") != 1:
        raise ValueError("Invalid artifact pointer schema")
    run_id = pointer.get("run_id")
    if not isinstance(run_id, str):
        raise ValueError("Artifact pointer is missing run_id")
    _validate_run_id(run_id)
    version = directory / "runs" / run_id
    paths = version / "model.joblib", version / "metadata.json"
    for path, key in zip(paths, ("model_sha256", "metadata_sha256")):
        if not path.is_file() or _sha256(path) != pointer.get(key):
            raise ValueError(f"Artifact integrity check failed: {path.name}")
    return paths


def load_artifact(output_dir: str | Path):
    model_path, metadata_path = resolve_artifact_paths(output_dir)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if "artifact_schema_version" in metadata and metadata.get("run_id") != model_path.parent.name:
        raise ValueError("Artifact model and metadata run IDs differ")
    return joblib.load(model_path), metadata

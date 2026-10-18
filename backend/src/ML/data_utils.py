"""Load and validate the shared ML splits used by Logistic Regression/SVM.

This module deliberately consumes the split artifacts produced by
``scripts.split_data``.  It never creates a new split or modifies those files.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
from sklearn.model_selection import PredefinedSplit


TRAIN_TEST_COLUMNS = ("message_id", "text_raw", "text", "label", "group_id")
FOLD_COLUMNS = ("message_id", "fold_id")


class DataValidationError(ValueError):
    """Raised when shared ML artifacts cannot safely be used for training."""


@dataclass(frozen=True)
class MLData:
    """Validated model inputs and the shared cross-validation assignment."""

    X_train: list[str]
    y_train: np.ndarray
    X_test: list[str]
    y_test: np.ndarray
    train_message_ids: tuple[str, ...]
    test_message_ids: tuple[str, ...]
    fold_ids: np.ndarray
    cv: PredefinedSplit


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "splits" / "ml"


def _read_csv(path: Path, required_columns: Sequence[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise DataValidationError(f"Required data file is missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames
        if headers is None:
            raise DataValidationError(f"{path}: CSV header is missing")
        duplicates = sorted({name for name in headers if headers.count(name) > 1})
        if duplicates:
            raise DataValidationError(f"{path}: duplicate CSV columns: {duplicates}")
        missing = [column for column in required_columns if column not in headers]
        if missing:
            raise DataValidationError(f"{path}: missing required columns: {missing}")
        rows = list(reader)
    if not rows:
        raise DataValidationError(f"{path}: file contains no data rows")
    return rows


def _require_nonempty(value: object, path: Path, column: str, row_number: int) -> str:
    if value is None or not str(value).strip():
        raise DataValidationError(f"{path}: row {row_number} has missing or blank {column}")
    return str(value)


def _validate_dataset(rows: list[dict[str, str]], path: Path) -> tuple[list[str], np.ndarray, tuple[str, ...], set[str]]:
    ids: list[str] = []
    texts: list[str] = []
    labels: list[int] = []
    groups: set[str] = set()
    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        message_id = _require_nonempty(row.get("message_id"), path, "message_id", row_number)
        if message_id in seen_ids:
            raise DataValidationError(f"{path}: duplicate message_id {message_id!r}")
        seen_ids.add(message_id)
        text = _require_nonempty(row.get("text"), path, "text", row_number)
        group_id = _require_nonempty(row.get("group_id"), path, "group_id", row_number)
        raw_label = _require_nonempty(row.get("label"), path, "label", row_number)
        if raw_label.strip() not in {"0", "1"}:
            raise DataValidationError(f"{path}: row {row_number} has invalid label {raw_label!r}; expected 0 or 1")
        ids.append(message_id)
        texts.append(text)
        labels.append(int(raw_label.strip()))
        groups.add(group_id)
    y = np.asarray(labels, dtype=np.int64)
    if set(y.tolist()) != {0, 1}:
        raise DataValidationError(f"{path}: dataset must contain both labels 0 (Ham) and 1 (Scam)")
    return texts, y, tuple(ids), groups


def _validate_folds(rows: list[dict[str, str]], path: Path, train_ids: tuple[str, ...], n_splits: int | None) -> np.ndarray:
    assignments: dict[str, int] = {}
    for row_number, row in enumerate(rows, start=2):
        message_id = _require_nonempty(row.get("message_id"), path, "message_id", row_number)
        if message_id in assignments:
            raise DataValidationError(f"{path}: duplicate fold assignment for message_id {message_id!r}")
        raw_fold = _require_nonempty(row.get("fold_id"), path, "fold_id", row_number)
        try:
            fold_id = int(raw_fold)
        except ValueError as exc:
            raise DataValidationError(f"{path}: row {row_number} has non-integer fold_id {raw_fold!r}") from exc
        if str(fold_id) != raw_fold.strip():
            raise DataValidationError(f"{path}: row {row_number} has invalid fold_id {raw_fold!r}")
        assignments[message_id] = fold_id

    train_id_set = set(train_ids)
    missing = sorted(train_id_set - assignments.keys())
    extra = sorted(assignments.keys() - train_id_set)
    if missing:
        raise DataValidationError(f"{path}: missing fold assignments for train IDs, e.g. {missing[:3]}")
    if extra:
        raise DataValidationError(f"{path}: fold assignments contain IDs outside train.csv, e.g. {extra[:3]}")

    ordered = np.asarray([assignments[message_id] for message_id in train_ids], dtype=np.int64)
    expected = set(range(n_splits)) if n_splits is not None else set(range(int(ordered.max()) + 1))
    if n_splits is not None and n_splits < 2:
        raise DataValidationError("manifest.json: split.n_splits must be at least 2")
    if not expected or set(ordered.tolist()) != expected:
        convention = f"0..{n_splits - 1}" if n_splits is not None else "a contiguous range starting at 0"
        raise DataValidationError(f"{path}: fold_id values must be exactly {convention}")
    return ordered


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest(path: Path | None, data_dir: Path, explicit: bool) -> tuple[dict | None, int | None]:
    if path is None:
        candidate = data_dir.parent / "manifest.json"
        if not candidate.is_file():
            return None, None
        path = candidate
    if not path.is_file():
        if explicit:
            raise DataValidationError(f"Manifest file is missing: {path}")
        return None, None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataValidationError(f"Could not read manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise DataValidationError(f"{path}: manifest must be a JSON object")
    split = manifest.get("split", {})
    n_splits = split.get("n_splits") if isinstance(split, dict) else None
    if n_splits is not None or isinstance(split, dict) and "n_splits" in split:
        if not isinstance(n_splits, int):
            raise DataValidationError(f"{path}: split.n_splits must be an integer")
    hashes = manifest.get("output_sha256")
    if isinstance(hashes, dict):
        for filename in ("train.csv", "test.csv", "cv_folds.csv"):
            key = f"splits/ml/{filename}"
            if key in hashes:
                artifact = data_dir / filename
                if not artifact.is_file():
                    raise DataValidationError(f"Required data file is missing: {artifact}")
                actual = _sha256(artifact)
                if hashes[key] != actual:
                    raise DataValidationError(
                        f"{path}: SHA-256 mismatch for {key}; expected {hashes[key]}, got {actual}"
                    )
    return manifest, n_splits


def _validate_cv_class_coverage(y_train: np.ndarray, fold_ids: np.ndarray, fold_path: Path) -> None:
    for fold_id in sorted(set(fold_ids.tolist())):
        validation = y_train[fold_ids == fold_id]
        training = y_train[fold_ids != fold_id]
        if set(validation.tolist()) != {0, 1}:
            raise DataValidationError(f"{fold_path}: fold {fold_id} must contain both Ham and Scam for metrics")
        if set(training.tolist()) != {0, 1}:
            raise DataValidationError(f"{fold_path}: training complement for fold {fold_id} must contain both labels")


def build_predefined_split(fold_ids: Sequence[int]) -> PredefinedSplit:
    """Create the shared sklearn split; item order must match ``X_train`` exactly."""
    return PredefinedSplit(test_fold=np.asarray(fold_ids, dtype=np.int64))


def load_ml_data(data_dir: str | Path | None = None, manifest_path: str | Path | None = None) -> MLData:
    """Load the shared ML train/test/CV artifacts without depending on the CWD.

    ``data_dir`` may point to a test fixture directory containing the three ML
    CSVs.  If a sibling ``manifest.json`` is present (or ``manifest_path`` is
    supplied), its available SHA-256 entries are verified before use.
    """
    resolved_data_dir = Path(data_dir) if data_dir is not None else _default_data_dir()
    resolved_data_dir = resolved_data_dir.resolve()
    train_path, test_path, fold_path = (resolved_data_dir / name for name in ("train.csv", "test.csv", "cv_folds.csv"))
    explicit_manifest = manifest_path is not None
    resolved_manifest = Path(manifest_path).resolve() if explicit_manifest else None

    # Check hashes before accepting values from the artifacts.
    _, n_splits = _load_manifest(resolved_manifest, resolved_data_dir, explicit_manifest)
    train_rows = _read_csv(train_path, TRAIN_TEST_COLUMNS)
    test_rows = _read_csv(test_path, TRAIN_TEST_COLUMNS)
    fold_rows = _read_csv(fold_path, FOLD_COLUMNS)
    X_train, y_train, train_ids, train_groups = _validate_dataset(train_rows, train_path)
    X_test, y_test, test_ids, test_groups = _validate_dataset(test_rows, test_path)
    overlapping_ids = sorted(set(train_ids) & set(test_ids))
    if overlapping_ids:
        raise DataValidationError(f"train.csv and test.csv overlap on message_id, e.g. {overlapping_ids[:3]}")
    overlapping_groups = sorted(train_groups & test_groups)
    if overlapping_groups:
        raise DataValidationError(f"train.csv and test.csv overlap on group_id, e.g. {overlapping_groups[:3]}")
    fold_ids = _validate_folds(fold_rows, fold_path, train_ids, n_splits)
    _validate_cv_class_coverage(y_train, fold_ids, fold_path)
    return MLData(X_train, y_train, X_test, y_test, train_ids, test_ids, fold_ids, build_predefined_split(fold_ids))

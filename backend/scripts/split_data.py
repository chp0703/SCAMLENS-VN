"""Deterministic grouped splits for ML CV and DL/JEV, sharing one test set."""

import argparse
from collections import Counter
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sklearn.model_selection import StratifiedGroupKFold

from scripts.dataset import DATA_COLUMNS, describe, read_csv, sha256, validate_serialization, write_csv, write_json

SEED = 42
N_FOLDS = 5
SPLIT_FILES = {
    "ml/train.csv": DATA_COLUMNS,
    "ml/test.csv": DATA_COLUMNS,
    "ml/cv_folds.csv": ["message_id", "fold_id"],
    "dl_jev/train.csv": DATA_COLUMNS,
    "dl_jev/val.csv": DATA_COLUMNS,
    "dl_jev/test.csv": DATA_COLUMNS,
}


def require_both_classes(rows: list[dict], name: str) -> None:
    if {int(row["label"]) for row in rows} != {0, 1}:
        raise ValueError(f"{name} must contain both classes; no random fallback is allowed")


def grouped_folds(rows: list[dict], seed: int, name: str) -> list[int]:
    require_both_classes(rows, name)
    for label in (0, 1):
        groups = {row["group_id"] for row in rows if int(row["label"]) == label}
        if len(groups) < N_FOLDS:
            raise ValueError(f"{name}: class {label} has {len(groups)} groups, needs at least {N_FOLDS}")
    splitter = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
    assignment = [-1] * len(rows)
    for fold, (train_indices, val_indices) in enumerate(splitter.split(
        [0] * len(rows), [int(row["label"]) for row in rows], [row["group_id"] for row in rows]
    )):
        training, validation = [rows[i] for i in train_indices], [rows[i] for i in val_indices]
        require_both_classes(training, f"{name} fold {fold} training")
        require_both_classes(validation, f"{name} fold {fold} validation")
        assert_disjoint(training, validation, f"{name} fold {fold}")
        for index in val_indices:
            if assignment[index] != -1:
                raise ValueError("Repeated CV validation membership")
            assignment[index] = fold
    if -1 in assignment:
        raise ValueError("Missing CV validation membership")
    return assignment


def assert_disjoint(left: list[dict], right: list[dict], name: str) -> None:
    for column in ("message_id", "text", "group_id"):
        if {row[column] for row in left} & {row[column] for row in right}:
            raise ValueError(f"Leakage in {name}: overlapping {column}")


def validate_clean(rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Clean dataset is empty")
    for row in rows:
        if any(key not in row for key in DATA_COLUMNS) or any(not row[key] for key in ("message_id", "text", "group_id")):
            raise ValueError("Clean dataset has missing fields")
        if str(row["label"]) not in {"0", "1"}:
            raise ValueError("Clean dataset has an invalid label")
    for key in ("message_id", "text"):
        if len({row[key] for row in rows}) != len(rows):
            raise ValueError(f"Clean dataset has duplicate {key}")


def create_splits(rows: list[dict], seed: int = SEED) -> dict[str, list[dict]]:
    validate_clean(rows)
    rows = sorted(rows, key=lambda row: row["message_id"])
    outer = grouped_folds(rows, seed, "outer split")
    train = [row for row, fold in zip(rows, outer) if fold != 0]
    test = [row for row, fold in zip(rows, outer) if fold == 0]
    inner = grouped_folds(train, seed, "train CV")
    splits = {
        "ml/train.csv": train,
        "ml/test.csv": test,
        "ml/cv_folds.csv": [dict(message_id=row["message_id"], fold_id=fold) for row, fold in zip(train, inner)],
        "dl_jev/train.csv": [row for row, fold in zip(train, inner) if fold != 0],
        "dl_jev/val.csv": [row for row, fold in zip(train, inner) if fold == 0],
        "dl_jev/test.csv": test,
    }
    validate_splits(rows, splits)
    return splits


def validate_splits(rows: list[dict], splits: dict[str, list[dict]]) -> dict:
    validate_clean(rows)
    train, test = splits["ml/train.csv"], splits["ml/test.csv"]
    dl_train, val = splits["dl_jev/train.csv"], splits["dl_jev/val.csv"]
    ids = lambda data: [row["message_id"] for row in data]
    if splits["dl_jev/test.csv"] != test:
        raise ValueError("ML and DL/JEV test rows/order differ")
    for name in SPLIT_FILES:
        if name == "ml/cv_folds.csv":
            continue
        validate_clean(splits[name])
        require_both_classes(splits[name], name)
    for left, right, name in ((train, test, "ML train/test"), (dl_train, val, "DL train/val"),
                               (dl_train, test, "DL train/test"), (val, test, "DL val/test")):
        assert_disjoint(left, right, name)
    if Counter(ids(train) + ids(test)) != Counter(ids(rows)):
        raise ValueError("ML split does not account for every clean row exactly once")
    if Counter(ids(dl_train) + ids(val)) != Counter(ids(train)):
        raise ValueError("DL train + val must equal ML train")
    originals = {row["message_id"]: row for row in rows}
    for name in SPLIT_FILES:
        if name != "ml/cv_folds.csv" and any(row != originals[row["message_id"]] for row in splits[name]):
            raise ValueError(f"Split changed row content: {name}")
    fold_rows = splits["ml/cv_folds.csv"]
    if Counter(ids(fold_rows)) != Counter(ids(train)):
        raise ValueError("CV must include every ML train ID exactly once")
    assignments = {row["message_id"]: int(row["fold_id"]) for row in fold_rows}
    if set(assignments.values()) != set(range(N_FOLDS)):
        raise ValueError("CV fold IDs must be 0..4")
    fold_stats = {}
    for fold in range(N_FOLDS):
        training = [row for row in train if assignments[row["message_id"]] != fold]
        validation = [row for row in train if assignments[row["message_id"]] == fold]
        require_both_classes(training, f"CV {fold} training")
        require_both_classes(validation, f"CV {fold} validation")
        assert_disjoint(training, validation, f"CV {fold}")
        fold_stats[str(fold)] = describe(validation)
    if ids(val) != [row["message_id"] for row in train if assignments[row["message_id"]] == 0]:
        raise ValueError("DL validation must equal CV fold 0")
    return dict(id_text_group_disjoint=True, clean_rows_accounted=True, shared_test_identical=True,
                dl_union_equals_ml_train=True, cv_train_ids_once=True, cv_fold0_equals_dl_val=True,
                all_partitions_have_both_classes=True, cv_validation_statistics=fold_stats)


def save_splits(directory: Path, splits: dict[str, list[dict]]) -> dict:
    directory = directory.resolve()
    raw_dir = (Path(__file__).resolve().parents[1] / "data/raw").resolve()
    if directory == raw_dir or raw_dir in directory.parents:
        raise ValueError("Split output must not overwrite raw data")
    hashes = {}
    for name, columns in SPLIT_FILES.items():
        path = directory / name
        write_csv(path, splits[name], columns)
        validate_serialization(path, splits[name], columns)
        hashes[name] = sha256(path)
    if hashes["ml/test.csv"] != hashes["dl_jev/test.csv"]:
        raise ValueError("Shared test CSV hashes differ")
    return hashes


def split_config(seed: int = SEED) -> dict:
    return dict(algorithm="StratifiedGroupKFold", n_splits=N_FOLDS, shuffle=True, random_state=seed,
                outer_test_fold=0, inner_dl_validation_fold=0,
                target_fractions=dict(ml=[0.8, 0.2], dl_jev=[0.64, 0.16, 0.2]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    backend = Path(__file__).resolve().parents[1]
    parser.add_argument("--input", type=Path, default=backend / "data/processed/clean.csv")
    parser.add_argument("--output-dir", type=Path, default=backend / "data/splits")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    if args.input.resolve() in {(args.output_dir / name).resolve() for name in (*SPLIT_FILES, "manifest.json")}:
        raise ValueError("Split output must not overwrite its input CSV")
    rows = read_csv(args.input)
    for row in rows:
        row["label"] = int(row["label"])
    splits = create_splits(rows, args.seed)
    checks = validate_splits(rows, splits)
    hashes = save_splits(args.output_dir, splits)
    # A split-only invocation intentionally records its more limited provenance.
    write_json(args.output_dir / "manifest.json", dict(status="provisional", scope="split_only",
               input_sha256=sha256(args.input), split=split_config(args.seed), checks=checks, output_sha256=hashes))
    print("Splits written; provisional. Run prepare_data.py for full source audit and report.")


if __name__ == "__main__":
    main()

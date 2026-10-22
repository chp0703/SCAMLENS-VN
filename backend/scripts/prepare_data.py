"""Prepare audited SMS data, shared grouped splits and an append-only report."""

import argparse
from collections import Counter
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.preprocessing import RULES_VERSION, TOKENS, normalize_text
from scripts.dataset import (
    ACCOUNT_COLUMNS, DATA_COLUMNS, DUPLICATE_COLUMNS, EDGE_COLUMNS, GROUP_COLUMNS, OUTLIER_COLUMNS,
    clean_source, describe, group_similar, length_analysis, read_csv, sha256,
    validate_serialization, write_csv, write_json,
)
from scripts.reporting import append_report
from scripts.split_data import SEED, create_splits, save_splits, split_config, validate_splits

BACKEND = Path(__file__).resolve().parents[1]
REVIEW_COLUMNS = ["source_row", "message_id", "text_raw", "text", "label", "reason"]


def run_tests() -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(BACKEND / "tests"), "-p", "test_preprocessing.py", "-v"],
        cwd=BACKEND, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError("Preprocessing tests failed:\n" + result.stdout + result.stderr)
    match = re.search(r"Ran (\d+) tests?", result.stderr)
    if not match or int(match.group(1)) == 0:
        raise RuntimeError("No preprocessing tests were executed")
    return dict(status="PASS", tests_run=int(match.group(1)))


def validate_accounting(rows: list[dict], accounting: list[dict], duplicates: list[dict]) -> None:
    if len({row["message_id"] for row in accounting}) != len(accounting):
        raise ValueError("Accounting has repeated source IDs")
    if any(row["status"] not in {"kept", "duplicate", "quarantined", "rejected"} for row in accounting):
        raise ValueError("Unaccounted source row")
    kept_ids = {row["message_id"] for row in rows}
    if kept_ids != {row["message_id"] for row in accounting if row["status"] == "kept"}:
        raise ValueError("Accounting does not match clean representatives")
    expected = {(row["message_id"], row["representative_id"]) for row in accounting if row["status"] == "duplicate"}
    if expected != {(row["message_id"], row["representative_id"]) for row in duplicates}:
        raise ValueError("Duplicate map does not match accounting")
    if any(row["representative_id"] not in kept_ids for row in duplicates):
        raise ValueError("Duplicate has no clean representative")
    if any(normalize_text(row["text_raw"]) != row["text"] or normalize_text(row["text"]) != row["text"] for row in rows):
        raise ValueError("Normalization round-trip/idempotence failed")


def prepare(source: Path, data_dir: Path, report_dir: Path, seed: int = SEED,
            threshold: float = 0.85, test_result: dict | None = None) -> tuple[dict, Path]:
    source, data_dir, report_dir = source.resolve(), data_dir.resolve(), report_dir.resolve()
    # Do not allow custom output paths to replace the source CSV or other raw inputs.
    raw_dir = (BACKEND / "data/raw").resolve()
    for output in (data_dir / "processed", data_dir / "splits", report_dir):
        if output == source or output in source.parents or output == raw_dir or raw_dir in output.parents:
            raise ValueError("Output paths must not overwrite raw/source data")
    source_hash = sha256(source)
    rows, accounting, duplicates = clean_source(source)
    edges, groups = group_similar(rows, threshold)
    length_stats, outliers = length_analysis(rows)
    validate_accounting(rows, accounting, duplicates)
    splits = create_splits(rows, seed)
    checks = validate_splits(rows, splits)
    checks.update(source_accounting_complete=True, normalized_raw_roundtrip=True, normalization_idempotent=True)
    original = {row["message_id"].strip(): row for row in read_csv(source)}

    def review_rows(status):
        return [dict(source_row=entry["source_row"], message_id=entry["message_id"],
                     text_raw=original[entry["message_id"]]["message"],
                     text=normalize_text(original[entry["message_id"]]["message"]),
                     label=original[entry["message_id"]]["label"], reason=entry["reason"])
                for entry in accounting if entry["status"] == status]

    processed_files = {
        "clean.csv": (rows, DATA_COLUMNS),
        "accounting.csv": (accounting, ACCOUNT_COLUMNS),
        "duplicates.csv": (duplicates, DUPLICATE_COLUMNS),
        "rejected.csv": (review_rows("rejected"), REVIEW_COLUMNS),
        "quarantine.csv": (review_rows("quarantined"), REVIEW_COLUMNS),
        "near_duplicate_pairs.csv": (edges, EDGE_COLUMNS),
        "groups.csv": (groups, GROUP_COLUMNS),
        "length_outliers.csv": (outliers, OUTLIER_COLUMNS),
    }
    status_counts = Counter(row["status"] for row in accounting)
    source_meta = source.with_name("source.json")
    provenance = json.loads(source_meta.read_text(encoding="utf-8-sig")) if source_meta.exists() else None
    manifest = dict(
        schema_version=1, status="provisional", scope="full_preprocessing",
        source=dict(path=str(source), sha256=source_hash, declared_metadata=provenance),
        rules=dict(version=RULES_VERSION, unicode="NFC", lowercase=True, whitespace="collapse_and_trim",
                   reserved_tokens=list(TOKENS), entity_order=["URL", "EMAIL", "PHONE"],
                   url="http(s):// or www.; trailing punctuation retained",
                   phone="Vietnam mobile 03/05/07/08/09 (10 digits), landline 02 (11 digits); +84/0084 supported",
                   duplicate_representative="lexicographically_smallest_message_id",
                   conflicting_exact_labels="quarantine_all", near_duplicate="character_5gram_set_jaccard_connected_components",
                   near_duplicate_threshold=threshold, large_group_min_size=10, length_outlier="1.5 IQR; retained",
                   label_mapping={"0": "Ham", "1": "Scam (source includes spam/scam)"}),
        split=split_config(seed),
        relationships=dict(shared_test="ml/test.csv == dl_jev/test.csv byte-for-byte",
                           train_pool="ml/train.csv == union(dl_jev/train.csv, dl_jev/val.csv)",
                           dl_validation="ml/cv_folds.csv fold_id=0"),
        dependencies={name: version(name) for name in ("scikit-learn", "numpy", "scipy", "joblib", "threadpoolctl")},
        python=platform.python_version(),
        counts=dict(source=len(accounting), clean=len(rows), accounting={status: status_counts[status] for status in
                    ("kept", "duplicate", "quarantined", "rejected")},
                    reasons=dict(sorted(Counter(row["reason"] for row in accounting if row["reason"]).items())),
                    source_labels=dict(sorted(Counter(row["label"].strip() for row in original.values()).items())),
                    clean_distribution=describe(rows)),
        partitions={name: describe(data) for name, data in splits.items() if name != "ml/cv_folds.csv"},
        length_statistics=length_stats,
        review=dict(pending_groups=sum(group["review_status"] == "pending" for group in groups),
                    large_groups=sum(group["size"] >= 10 for group in groups),
                    mixed_label_groups=sum(group["ham"] > 0 and group["scam"] > 0 for group in groups),
                    largest_group=max(group["size"] for group in groups),
                    length_outliers=len(outliers), near_duplicate_pairs=len(edges)),
        checks=checks,
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    # Stage and validate all CSVs before replacing a previous successful run.
    with tempfile.TemporaryDirectory(prefix=".preprocess-", dir=data_dir) as temporary:
        stage = Path(temporary)
        output_hashes = {}
        for name, (data, columns) in processed_files.items():
            path = stage / "processed" / name
            write_csv(path, data, columns)
            validate_serialization(path, data, columns)
            output_hashes["processed/" + name] = sha256(path)
        output_hashes.update({"splits/" + key: value for key, value in save_splits(stage / "splits", splits).items()})
        if sha256(source) != source_hash:
            raise ValueError("Source changed while preprocessing")
        checks.update(source_sha256_unchanged=True, csv_utf8_bom_roundtrip=True, shared_test_hash_identical=True)
        manifest["output_sha256"] = dict(sorted(output_hashes.items()))
        write_json(stage / "splits/manifest.json", manifest)
        for name in output_hashes:
            target = data_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage / name, target)
        os.replace(stage / "splits/manifest.json", data_dir / "splits/manifest.json")
    report = append_report(report_dir, manifest, test_result or dict(status="NOT RUN (use --run-tests)"))
    return manifest, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=BACKEND / "data/raw/vietnamese_sms_dataset/full_dataset.csv")
    parser.add_argument("--data-dir", type=Path, default=BACKEND / "data")
    parser.add_argument("--report-dir", type=Path, default=BACKEND / "report")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--similarity-threshold", type=float, default=0.85)
    parser.add_argument("--run-tests", action="store_true")
    args = parser.parse_args()
    tests = run_tests() if args.run_tests else None
    manifest, report = prepare(args.source, args.data_dir, args.report_dir, args.seed, args.similarity_threshold, tests)
    print(json.dumps(dict(status=manifest["status"], counts=manifest["counts"],
                          partitions=manifest["partitions"], review=manifest["review"], report=str(report)), indent=2))


if __name__ == "__main__":
    main()

"""Audit SMS data and generate reproducible, provisional grouped splits.

Run from backend: python src/ML/prepare_data.py
This step uses only the Python standard library and never fits a vectorizer.
"""

import argparse
import csv
import hashlib
import json
import math
import random
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.preprocessing import (
    PREPROCESSING_VERSION,
    duplicate_key,
    normalize_text,
    template_tokens,
)
from src.ML.reporting import write_preprocess_report

PREPARATION_VERSION = "sms-grouped-preparation-v2-utf8bom"
CSV_ENCODING = "utf-8-sig"
SPLIT_NAMES = ("train", "validation", "test")
SPLIT_RATIOS = (0.70, 0.15, 0.15)
REQUIRED_COLUMNS = ("message_id", "date", "message", "label")
OUTPUT_COLUMNS = (
    "message_id", "date", "message", "text", "label", "group_id",
    "source_ids", "source_count",
)
_PHONE = re.compile(r"(?<!\w)(?:\+84|0084|0)(?:[ .-]?\d){9,10}(?!\w)")
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.IGNORECASE)
_LONG_NUMBER = re.compile(r"(?<!\d)\d{8,19}(?!\d)")
_OTP = re.compile(
    r"\b(?:otp|pin|mã\s+(?:xác\s+thực|bảo\s+mật)|ma\s+(?:xac\s+thuc|bao\s+mat))"
    r"\b[^\d\n]{0,60}(\d{4,8})(?!\d)",
    re.IGNORECASE,
)
PII_PATTERNS = {
    "phone_candidate": _PHONE,
    "email_candidate": _EMAIL,
    "long_number_candidate": _LONG_NUMBER,
    "otp_or_pin_candidate": _OTP,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding=CSV_ENCODING, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_source(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(REQUIRED_COLUMNS):
            raise ValueError(f"Expected CSV columns {REQUIRED_COLUMNS}; received {reader.fieldnames}")
        rows = list(reader)
    if not rows:
        raise ValueError("Source dataset is empty")
    seen_ids = set()
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed CSV row")
        identifier = row["message_id"]
        if not identifier.strip() or identifier != identifier.strip() or identifier in seen_ids:
            raise ValueError("Missing, whitespace-padded or duplicate message_id")
        seen_ids.add(identifier)
        if row["label"] not in {"0", "1"}:
            raise ValueError(f"Invalid label for {identifier}")
        if not normalize_text(row["message"]):
            raise ValueError(f"Empty normalized message for {identifier}")
    return sorted(rows, key=lambda row: row["message_id"])


def audit_source(rows: list[dict]) -> tuple[dict, list[dict]]:
    exact = defaultdict(list)
    normalized = defaultdict(list)
    privacy_review = []
    invalid_dates = []
    dates = []
    placeholders = Counter()
    for row in rows:
        message = row["message"]
        exact[message].append(row)
        normalized[duplicate_key(message)].append(row)
        categories = [name for name, pattern in PII_PATTERNS.items() if pattern.search(message)]
        if categories:
            privacy_review.append({"message_id": row["message_id"], "categories": ";".join(categories)})
        placeholders.update(re.findall(r"\[[A-Z_]+\]", message))
        if row["date"].strip():
            try:
                dates.append(datetime.strptime(row["date"], "%d/%m/%Y").date().isoformat())
            except ValueError:
                invalid_dates.append(row["message_id"])
    conflict_groups = [group for group in normalized.values() if len({r["label"] for r in group}) > 1]
    lengths = sorted(len(normalize_text(row["message"])) for row in rows)
    return {
        "raw_rows": len(rows),
        "labels": dict(sorted(Counter(row["label"] for row in rows).items())),
        "missing_by_column": {key: sum(not row[key].strip() for row in rows) for key in REQUIRED_COLUMNS},
        "unique_ids": len(rows),
        "exact_unique_messages": len(exact),
        "exact_duplicate_extra_rows": len(rows) - len(exact),
        "exact_conflicting_label_groups": sum(len({r["label"] for r in group}) > 1 for group in exact.values()),
        "normalized_unique_messages": len(normalized),
        "normalized_duplicate_extra_rows": len(rows) - len(normalized),
        "normalized_conflicting_label_groups": len(conflict_groups),
        "conflicting_source_ids": sorted(r["message_id"] for group in conflict_groups for r in group),
        "invalid_date_ids": invalid_dates,
        "date_range": {"min": min(dates) if dates else None, "max": max(dates) if dates else None},
        "text_lengths": {"min": lengths[0], "median": lengths[len(lengths) // 2], "max": lengths[-1]},
        "normalization_changed_rows": sum(normalize_text(row["message"]) != row["message"] for row in rows),
        "source_unicode_replacement_rows": sum("\ufffd" in row["message"] for row in rows),
        "source_c1_control_rows": sum(any(0x80 <= ord(char) <= 0x9f for char in row["message"]) for row in rows),
        "source_mathematical_unicode_rows": sum(any(unicodedata.name(char, "").startswith("MATHEMATICAL ") for char in row["message"]) for row in rows),
        "placeholder_occurrences": dict(sorted(placeholders.items())),
        "privacy_candidate_rows": len(privacy_review),
        "privacy_candidates_by_category": {name: sum(name in row["categories"].split(";") for row in privacy_review) for name in PII_PATTERNS},
        "privacy_note": "Regex candidates only; includes public contacts, dates and device IDs. Not a complete PII audit or a declaration of a privacy breach.",
    }, privacy_review


def deduplicate(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    buckets = defaultdict(list)
    for row in rows:
        buckets[duplicate_key(row["message"])].append(row)
    records, conflicts, duplicate_map = [], [], []
    for key, bucket in sorted(buckets.items()):
        bucket = sorted(bucket, key=lambda row: row["message_id"])
        if len({row["label"] for row in bucket}) > 1:
            for row in bucket:
                conflicts.append({**row, "reason": "conflicting_labels_after_normalization", "normalized_sha256": stable_hash(key)})
            continue
        representative = bucket[0]
        records.append({
            **representative,
            "text": normalize_text(representative["message"]),
            "group_id": "",
            "source_ids": json.dumps([row["message_id"] for row in bucket], separators=(",", ":")),
            "source_count": len(bucket),
        })
        for row in bucket:
            duplicate_map.append({"source_id": row["message_id"], "representative_id": representative["message_id"], "normalized_sha256": stable_hash(key)})
    return sorted(records, key=lambda row: row["message_id"]), conflicts, duplicate_map


def group_templates(records: list[dict], threshold: float = 0.85) -> tuple[list[list[dict]], list[dict]]:
    """Union exact signatures and token-set Jaccard neighbors, without labels.

    Transitive groups prevent related templates crossing splits. A matching
    heuristic cannot prove that all semantic template families were found.
    """
    parent = list(range(len(records)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    signatures = [template_tokens(row["text"]) for row in records]
    token_sets = [set(signature) for signature in signatures]
    signature_first = {}
    postings = defaultdict(list)
    edges = []
    for index, signature in enumerate(signatures):
        if signature and signature in signature_first:
            other = signature_first[signature]
            union(index, other)
            edges.append({"left_id": records[other]["message_id"], "right_id": records[index]["message_id"], "method": "exact_masked_template", "similarity": "1.000000"})
        elif signature:
            signature_first[signature] = index
        tokens = token_sets[index]
        if len(tokens) < 5:
            continue
        intersections = Counter()
        for token in sorted(tokens):
            intersections.update(postings[token])
        for other, intersection in sorted(intersections.items()):
            if signatures[other] == signature:
                continue
            union_size = len(tokens) + len(token_sets[other]) - intersection
            similarity = intersection / union_size
            if similarity >= threshold:
                union(index, other)
                edges.append({"left_id": records[other]["message_id"], "right_id": records[index]["message_id"], "method": "token_set_jaccard", "similarity": f"{similarity:.6f}"})
        for token in sorted(tokens):
            postings[token].append(index)
    components = defaultdict(list)
    for index, row in enumerate(records):
        components[find(index)].append(row)
    groups = []
    for group in components.values():
        identifier = "g_" + stable_hash("\n".join(sorted(duplicate_key(r["text"]) for r in group)))[:16]
        for row in group:
            row["group_id"] = identifier
        groups.append(sorted(group, key=lambda row: row["message_id"]))
    return sorted(groups, key=lambda group: group[0]["group_id"]), edges


def split_groups(groups: list[list[dict]], seed: int = 42, attempts: int = 64) -> dict[str, list[dict]]:
    """Seeded greedy whole-group allocation, balancing both label counts."""
    if len(groups) < 3:
        raise ValueError("At least three template groups are required for three splits")
    totals = Counter(row["label"] for group in groups for row in group)
    if set(totals) != {"0", "1"}:
        raise ValueError("Both labels must remain after deduplication and quarantine")
    targets = [[ratio * totals[label] for label in ("0", "1")] for ratio in SPLIT_RATIOS]

    def cost(counts):
        return sum((counts[s][label] - targets[s][i]) ** 2 / max(targets[s][i], 1) for s in range(3) for i, label in enumerate(("0", "1")))

    best = None
    for attempt in range(attempts):
        rng = random.Random(seed + attempt)
        ordered = list(groups)
        rng.shuffle(ordered)
        ordered.sort(key=len, reverse=True)
        counts = [Counter() for _ in range(3)]
        assignment = {name: [] for name in SPLIT_NAMES}
        for group in ordered:
            group_counts = Counter(row["label"] for row in group)
            deltas = []
            for split in range(3):
                delta = sum(
                    ((counts[split][label] + group_counts[label] - targets[split][i]) ** 2
                     - (counts[split][label] - targets[split][i]) ** 2) / max(targets[split][i], 1)
                    for i, label in enumerate(("0", "1"))
                )
                deltas.append(delta)
            split = min(range(3), key=lambda index: (deltas[index], index))
            counts[split].update(group_counts)
            assignment[SPLIT_NAMES[split]].extend(group)
        if any(not counts[s][label] for s in range(3) for label in ("0", "1")):
            continue
        score = cost(counts)
        if best is None or score < best[0]:
            best = score, assignment
    if best is None:
        raise ValueError("Unable to allocate both classes to every split without splitting groups")
    return {name: sorted(rows, key=lambda row: row["message_id"]) for name, rows in best[1].items()}


def verify_splits(splits: dict[str, list[dict]], edges: list[dict]) -> dict:
    owner = {}
    checks = {}
    for index, left in enumerate(SPLIT_NAMES):
        for row in splits[left]:
            for source_id in json.loads(row["source_ids"]):
                if source_id in owner:
                    raise ValueError("A source ID occurs in more than one output record")
                owner[source_id] = left
        for right in SPLIT_NAMES[index + 1:]:
            pair = f"{left}__{right}"
            checks[pair] = {}
            for key in ("group_id", "message_id", "text"):
                values_left = {duplicate_key(r[key]) if key == "text" else r[key] for r in splits[left]}
                values_right = {duplicate_key(r[key]) if key == "text" else r[key] for r in splits[right]}
                overlap = len(values_left & values_right)
                checks[pair][key] = overlap
                if overlap:
                    raise ValueError(f"Split leakage in {pair}: {key}")
    crossing = sum(owner[edge["left_id"]] != owner[edge["right_id"]] for edge in edges)
    if crossing:
        raise ValueError("Detected template edge crosses splits")
    checks["detected_template_edges_crossing_splits"] = crossing
    return checks


def verify_serialized_outputs(output_dir: Path, source_rows: list[dict], records: list[dict], conflicts: list[dict]) -> dict:
    """Read disk artifacts back and check encoding, text fidelity and accounting."""
    source_by_id = {row["message_id"]: row for row in source_rows}
    represented_ids = [identifier for row in records for identifier in json.loads(row["source_ids"])]
    represented_ids.extend(row["message_id"] for row in conflicts)
    if len(represented_ids) != len(set(represented_ids)) or set(represented_ids) != set(source_by_id):
        raise ValueError("Source ID accounting failed")
    for path in output_dir.glob("*.csv"):
        payload = path.read_bytes()
        if not payload.startswith(b"\xef\xbb\xbf") or payload.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"):
            raise ValueError(f"Missing or repeated UTF-8 BOM in {path.name}")
        payload.decode(CSV_ENCODING, errors="strict")
    for name, expected in [("clean", records), ("quarantine", conflicts)]:
        with (output_dir / f"{name}.csv").open(encoding=CSV_ENCODING, newline="") as handle:
            actual = list(csv.DictReader(handle))
        if len(actual) != len(expected):
            raise ValueError(f"Serialized row count mismatch in {name}")
        for row in actual:
            raw = source_by_id[row["message_id"]]["message"]
            if row["message"] != raw or (name == "clean" and row["text"] != normalize_text(raw)):
                raise ValueError(f"Unicode round-trip mismatch for {row['message_id']}")
    persisted_splits = {}
    for name in SPLIT_NAMES:
        with (output_dir / f"{name}.csv").open(encoding=CSV_ENCODING, newline="") as handle:
            persisted_splits[name] = list(csv.DictReader(handle))
        for row in persisted_splits[name]:
            raw = source_by_id[row["message_id"]]["message"]
            if row["message"] != raw or row["text"] != normalize_text(raw):
                raise ValueError(f"Unicode round-trip mismatch in {name}")
    if sorted(row["message_id"] for part in persisted_splits.values() for row in part) != sorted(row["message_id"] for row in records):
        raise ValueError("Serialized split accounting failed")
    verify_splits(persisted_splits, [])
    return {
        "csv_utf8_bom": True,
        "strict_utf8_decode": True,
        "raw_message_round_trip": True,
        "normalized_text_round_trip": True,
        "source_ids_accounted_for": len(represented_ids),
        "serialized_split_accounting": True,
        "serialized_split_leakage_checks": True,
    }


def run(input_path: Path, output_dir: Path, seed: int = 42, threshold: float = 0.85) -> dict:
    input_path, output_dir = input_path.resolve(), output_dir.resolve()
    if input_path.parent == output_dir or input_path.is_relative_to(output_dir):
        raise ValueError("Output directory must be separate from raw input")
    if not math.isfinite(threshold) or not 0 < threshold <= 1:
        raise ValueError("Jaccard threshold must be in (0, 1]")
    owned_files = {
        "clean.csv", "train.csv", "validation.csv", "test.csv", "quarantine.csv",
        "duplicate_map.csv", "template_review.csv", "template_edges.csv",
        "privacy_review.csv", "audit_report.json", "manifest.json",
    }
    if output_dir.exists() and any(path.name not in owned_files for path in output_dir.iterdir()):
        raise ValueError("Output directory contains unrelated files; select a dedicated directory")
    source_hash = sha256_file(input_path)
    original = None
    provenance = input_path.parent / "source.json"
    if provenance.exists():
        original = json.loads(provenance.read_text(encoding="utf-8-sig"))
        expected = original.get("sha256", {}).get(input_path.name)
        if expected and expected != source_hash:
            raise ValueError("Raw dataset hash differs from source.json")
    rows = read_source(input_path)
    audit, privacy_review = audit_source(rows)
    records, conflicts, duplicate_map = deduplicate(rows)
    groups, edges = group_templates(records, threshold)
    splits = split_groups(groups, seed)
    checks = verify_splits(splits, edges)
    if len(duplicate_map) + len(conflicts) != len(rows):
        raise ValueError("Source-row accounting failed")
    if sum(len(part) for part in splits.values()) != len(records):
        raise ValueError("Split-row accounting failed")
    if sha256_file(input_path) != source_hash:
        raise ValueError("Input changed during preparation")
    audit.update({
        "quarantined_source_rows": len(conflicts),
        "removed_duplicate_extra_rows": len(duplicate_map) - len(records),
        "clean_unique_rows": len(records),
        "clean_labels": dict(sorted(Counter(row["label"] for row in records).items())),
        "template_groups": len(groups),
        "multi_message_template_groups": sum(len(group) > 1 for group in groups),
        "mixed_label_template_groups": sum(len({r["label"] for r in group}) > 1 for group in groups),
        "largest_template_group": max(map(len, groups)),
        "template_edges": dict(sorted(Counter(edge["method"] for edge in edges).items())),
        "splits": {name: {"rows": len(part), "labels": dict(sorted(Counter(row["label"] for row in part).items())), "groups": len({row["group_id"] for row in part})} for name, part in splits.items()},
        "leakage_checks": checks,
        "split_status": "provisional_pending_template_and_privacy_review",
        "limitations": [
            "Jaccard matching groups lexical variants; it does not guarantee semantic template separation.",
            "Connected components may group dissimilar endpoints through intermediate messages; review template groups before freezing.",
            "Privacy checks flag candidates and may miss identifiers; no redaction is applied to model text.",
            "Mixed-label normalized duplicates are quarantined without assigning a new label.",
            "Missing dates are retained; dates and message IDs are metadata, not ML features.",
            "Both classes use the source label definition: legitimate vs combined spam/scam.",
            "No vectorizer or model is fitted and no test model metrics are computed.",
        ],
    })
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "clean.csv", OUTPUT_COLUMNS, records)
    for name, part in splits.items():
        write_csv(output_dir / f"{name}.csv", OUTPUT_COLUMNS, part)
    write_csv(output_dir / "quarantine.csv", (*REQUIRED_COLUMNS, "reason", "normalized_sha256"), conflicts)
    write_csv(output_dir / "duplicate_map.csv", ("source_id", "representative_id", "normalized_sha256"), duplicate_map)
    write_csv(output_dir / "template_edges.csv", ("left_id", "right_id", "method", "similarity"), edges)
    write_csv(output_dir / "privacy_review.csv", ("message_id", "categories"), privacy_review)
    reviews = []
    for group in groups:
        if len(group) > 1:
            reviews.append({
                "group_id": group[0]["group_id"],
                "unique_messages": len(group),
                "source_rows": sum(row["source_count"] for row in group),
                "labels": ";".join(sorted({row["label"] for row in group})),
                "representative_ids": json.dumps([row["message_id"] for row in group], separators=(",", ":")),
            })
    write_csv(output_dir / "template_review.csv", ("group_id", "unique_messages", "source_rows", "labels", "representative_ids"), reviews)
    audit["serialization_checks"] = verify_serialized_outputs(output_dir, rows, records, conflicts)
    audit["csv_encoding"] = CSV_ENCODING
    write_json(output_dir / "audit_report.json", audit)
    manifest = {
        "preparation_version": PREPARATION_VERSION,
        "preprocessing_version": PREPROCESSING_VERSION,
        "preparation_script_sha256": sha256_file(Path(__file__)),
        "preprocessing_script_sha256": sha256_file(BACKEND / "app/services/preprocessing.py"),
        "reporting_script_sha256": sha256_file(Path(__file__).with_name("reporting.py")),
        "python_version": sys.version.split()[0],
        "csv_encoding": CSV_ENCODING,
        "json_encoding": "utf-8",
        "source_file": input_path.name,
        "source_sha256": source_hash,
        "seed": seed,
        "split_ratios_target": dict(zip(SPLIT_NAMES, SPLIT_RATIOS)),
        "jaccard_threshold": threshold,
        "near_duplicate_min_unique_tokens": 5,
        "split_algorithm": "whole-group-label-balanced-greedy-64-attempts",
        "split_status": audit["split_status"],
        "model_input_column": "text",
        "deduplication": "one representative per normalized text; keep all source IDs; quarantine conflicting labels",
        "artifacts_sha256": {name: sha256_file(output_dir / name) for name in sorted(owned_files - {"manifest.json"})},
    }
    if original is not None:
        manifest["source_repository"] = original.get("source")
        manifest["source_revision"] = original.get("revision")
    write_json(output_dir / "manifest.json", manifest)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=BACKEND / "data/vietnamese_sms_dataset/full_dataset.csv")
    parser.add_argument("--output-dir", type=Path, default=BACKEND / "data/processed/sms_v1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--jaccard-threshold", type=float, default=0.85)
    parser.add_argument("--report-dir", type=Path, default=BACKEND / "report")
    parser.add_argument("--run-tests", action="store_true", help="Run preprocessing unittest suite before preparing data")
    args = parser.parse_args()
    unit_tests = None
    try:
        if args.run_tests:
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", str(BACKEND / "tests"), "-p", "test_preprocessing.py", "-v"],
                capture_output=True, text=True, encoding="utf-8",
            )
            print(result.stdout + result.stderr, file=sys.stderr, end="")
            count = re.search(r"Ran (\d+) tests?", result.stdout + result.stderr)
            unit_tests = {"status": "PASS" if result.returncode == 0 else "FAIL", "tests_run": int(count.group(1)) if count else None, "return_code": result.returncode}
            if result.returncode:
                raise RuntimeError("Preprocessing unittest suite failed; dataset preparation was not run")
        report = run(args.input, args.output_dir, args.seed, args.jaccard_threshold)
        manifest = json.loads((args.output_dir / "manifest.json").read_text(encoding="utf-8"))
        report_path = write_preprocess_report(args.report_dir, report, manifest, unit_tests=unit_tests)
    except Exception as error:
        report_path = write_preprocess_report(args.report_dir, unit_tests=unit_tests, failure=f"{type(error).__name__}: {error}")
        print(f"Preprocess failed: {error}\nReport: {report_path}", file=sys.stderr)
        raise SystemExit(1) from error
    summary = {key: report[key] for key in (
        "raw_rows", "exact_duplicate_extra_rows", "normalized_duplicate_extra_rows",
        "normalized_conflicting_label_groups", "quarantined_source_rows",
        "removed_duplicate_extra_rows", "clean_unique_rows", "clean_labels",
        "template_groups", "multi_message_template_groups", "mixed_label_template_groups",
        "largest_template_group", "privacy_candidate_rows", "privacy_candidates_by_category",
        "splits", "leakage_checks", "split_status",
    )}
    summary["csv_encoding"] = CSV_ENCODING
    summary["report_path"] = str(report_path)
    summary["unit_tests"] = unit_tests
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

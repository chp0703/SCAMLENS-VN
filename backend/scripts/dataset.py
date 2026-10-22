"""Auditable cleaning, similarity groups, statistics and CSV serialization."""

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from app.services.preprocessing import normalize_surface, normalize_text

DATA_COLUMNS = ["message_id", "text_raw", "text", "label", "group_id"]
ACCOUNT_COLUMNS = ["source_row", "message_id", "status", "reason", "representative_id"]
DUPLICATE_COLUMNS = ["message_id", "representative_id", "stage"]
EDGE_COLUMNS = ["left_id", "right_id", "similarity", "different_labels", "group_id"]
GROUP_COLUMNS = ["group_id", "size", "ham", "scam", "review_reason", "review_status"]
OUTLIER_COLUMNS = ["message_id", "label", "char_length", "word_length", "reason"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def clean_source(path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Return representatives, one accounting row per input, and duplicate mapping."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"message_id", "message", "label"}.issubset(reader.fieldnames or []):
            raise ValueError("Source must contain message_id, message, label")
        source = list(reader)
    if not source:
        raise ValueError("Source is empty")
    if any(None in row or any(value is None for value in row.values()) for row in source):
        raise ValueError("Malformed CSV record: extra or missing fields")
    ids = [row.get("message_id", "").strip() for row in source]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("Source message_id must be nonempty and unique")
    accounting, valid = [], []
    for number, (row, message_id) in enumerate(zip(source, ids), start=2):
        text_raw, label_raw = row["message"], row["label"].strip()
        entry = dict(source_row=number, message_id=message_id, status="", reason="", representative_id="")
        accounting.append(entry)
        if not text_raw.strip() or not label_raw:
            entry.update(status="rejected", reason="missing_text_or_label")
        elif label_raw not in {"0", "1"}:
            entry.update(status="rejected", reason="invalid_label")
        else:
            valid.append(dict(message_id=message_id, text_raw=text_raw, label=int(label_raw),
                              surface=normalize_surface(text_raw), text=normalize_text(text_raw), account=entry))

    surface_groups, final_groups = defaultdict(list), defaultdict(list)
    for row in valid:
        surface_groups[row["surface"]].append(row)
        final_groups[row["text"]].append(row)
    pre_conflicts = {key for key, rows in surface_groups.items() if len({r["label"] for r in rows}) > 1}
    clean, duplicates = [], []
    for rows in final_groups.values():
        before_conflict = any(row["surface"] in pre_conflicts for row in rows)
        if before_conflict or len({row["label"] for row in rows}) > 1:
            for row in rows:
                row["account"].update(status="quarantined", reason="label_conflict_before_masking" if before_conflict
                                      else "label_conflict_after_masking")
            continue
        representative = min(rows, key=lambda row: row["message_id"])
        representative["account"].update(status="kept", representative_id=representative["message_id"])
        clean.append({key: representative[key] for key in DATA_COLUMNS if key != "group_id"})
        for row in rows:
            if row is representative:
                continue
            stage = "before_masking" if row["surface"] == representative["surface"] else "after_masking"
            row["account"].update(status="duplicate", reason=stage, representative_id=representative["message_id"])
            duplicates.append(dict(message_id=row["message_id"], representative_id=representative["message_id"], stage=stage))
    return sorted(clean, key=lambda row: row["message_id"]), accounting, sorted(duplicates, key=lambda row: row["message_id"])


def char_grams(text: str) -> set[str]:
    return {text[index:index + 5] for index in range(len(text) - 4)}


def group_similar(rows: list[dict], threshold: float = 0.85) -> tuple[list[dict], list[dict]]:
    """Group every qualifying pair; connected components deliberately allow chains."""
    if not 0 < threshold <= 1:
        raise ValueError("Similarity threshold must be in (0, 1]")
    parents = list(range(len(rows)))

    def root(index):
        while index != parents[index]:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    grams = [char_grams(row["text"]) for row in rows]
    edges = []
    for left, a in enumerate(grams):
        for right in range(left + 1, len(rows)):
            b = grams[right]
            if not a or not b:
                similarity = float(rows[left]["text"] == rows[right]["text"])
            elif min(len(a), len(b)) / max(len(a), len(b)) < threshold:
                continue
            else:
                intersection = len(a & b)
                similarity = intersection / (len(a) + len(b) - intersection)
            if similarity >= threshold:
                parents[root(right)] = root(left)
                edges.append(dict(left_id=rows[left]["message_id"], right_id=rows[right]["message_id"],
                                  similarity=round(similarity, 8), different_labels=int(rows[left]["label"] != rows[right]["label"])))
    components = defaultdict(list)
    for index, row in enumerate(rows):
        components[root(index)].append(row)
    summaries = []
    for component in components.values():
        members = sorted(row["message_id"] for row in component)
        group_id = "g_" + hashlib.sha256(json.dumps(members).encode()).hexdigest()[:16]
        labels = Counter(row["label"] for row in component)
        reasons = []
        if len(component) > 1:
            reasons.append("near_duplicate")
        if len(component) >= 10:
            reasons.append("large_group")
        if len(labels) > 1:
            reasons.append("mixed_labels")
        for row in component:
            row["group_id"] = group_id
        summaries.append(dict(group_id=group_id, size=len(component), ham=labels[0], scam=labels[1],
                              review_reason=";".join(reasons), review_status="pending" if reasons else "not_required"))
    id_to_group = {row["message_id"]: row["group_id"] for row in rows}
    for edge in edges:
        edge["group_id"] = id_to_group[edge["left_id"]]
    return edges, sorted(summaries, key=lambda row: row["group_id"])


def quantile(values: list[int], fraction: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def length_analysis(rows: list[dict]) -> tuple[dict, list[dict]]:
    if not rows:
        raise ValueError("No usable rows remain after cleaning")
    stats, bounds = {}, {}
    for name, measure in (("char", len), ("word", lambda text: len(text.split()))):
        values = [measure(row["text"]) for row in rows]
        q1, q3 = quantile(values, 0.25), quantile(values, 0.75)
        lower, upper = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        stats[name] = dict(min=min(values), p25=q1, median=quantile(values, 0.5), p75=q3,
                           p95=quantile(values, 0.95), max=max(values), iqr_lower=lower, iqr_upper=upper)
        bounds[name] = lower, upper
    outliers = []
    for row in rows:
        sizes = dict(char=len(row["text"]), word=len(row["text"].split()))
        reasons = [name + "_iqr" for name, value in sizes.items() if not bounds[name][0] <= value <= bounds[name][1]]
        if reasons:
            outliers.append(dict(message_id=row["message_id"], label=row["label"], char_length=sizes["char"],
                                 word_length=sizes["word"], reason=";".join(reasons)))
    return stats, outliers


def describe(rows: list[dict]) -> dict:
    labels = Counter(int(row["label"]) for row in rows)
    return dict(rows=len(rows), ham=labels[0], scam=labels[1], scam_fraction=labels[1] / len(rows) if rows else 0,
                groups=len({row["group_id"] for row in rows}))


def validate_serialization(path: Path, expected: list[dict], columns: list[str]) -> None:
    data = path.read_bytes()
    if not data.startswith(b"\xef\xbb\xbf") or data.startswith(b"\xef\xbb\xbf" * 2):
        raise ValueError(f"Expected exactly one leading UTF-8 BOM: {path.name}")
    data.decode("utf-8-sig", errors="strict")
    actual = read_csv(path)
    wanted = [{key: str(row.get(key, "")) for key in columns} for row in expected]
    if actual != wanted:
        raise ValueError(f"CSV round-trip failed: {path.name}")

"""Persistent, provenance-only reports for ML training runs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import uuid

import joblib
import numpy as np
import sklearn


def default_report_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "experiments" / "logistic_regression" / "runs"


def new_run_context(run_type: str, report_dir: str | Path | None = None) -> dict:
    timestamp = datetime.now(timezone.utc)
    run_id = f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:8]}"
    directory = (Path(report_dir) if report_dir is not None else default_report_dir()).resolve()
    return {"run_id": run_id, "timestamp": timestamp.isoformat(), "run_type": run_type, "report_dir": directory}


def source_fingerprints(data_dir: str | Path | None, default_data_dir: Path) -> dict[str, str]:
    directory = (Path(data_dir) if data_dir is not None else default_data_dir).resolve()
    result: dict[str, str] = {}
    for filename in ("train.csv", "cv_folds.csv"):
        path = directory / filename
        if path.is_file():
            result[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def versions() -> dict[str, str]:
    return {
        "python": platform.python_version(), "scikit_learn": sklearn.__version__,
        "numpy": np.__version__, "joblib": joblib.__version__,
    }


def write_report(context: dict, payload: dict) -> tuple[Path, Path]:
    """Write paired JSON/Markdown reports, refusing to overwrite a run ID."""
    directory = context["report_dir"]
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"{context['run_id']}.json"
    md_path = directory / f"{context['run_id']}.md"
    if json_path.exists() or md_path.exists():
        raise FileExistsError(f"Report already exists for run {context['run_id']}")
    document = {**payload, "run_id": context["run_id"], "timestamp_utc": context["timestamp"], "run_type": context["run_type"]}
    json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = [f"# Logistic Regression {context['run_type']} run", "", f"- Run ID: `{context['run_id']}`", f"- Timestamp (UTC): {context['timestamp']}", f"- Status: {document.get('status', 'unknown')}", "", "## Summary", "", "```json", json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str), "```", ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path

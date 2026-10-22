"""Persistent, provenance-only reports for ML training runs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time
import uuid

import joblib
import numpy as np
import sklearn


def default_report_dir(model_key: str = "logistic_regression") -> Path:
    return Path(__file__).resolve().parents[2] / "experiments" / model_key / "runs"


def new_run_context(run_type: str, report_dir: str | Path | None = None, *,
                    model_key: str = "logistic_regression", model_name: str = "Logistic Regression") -> dict:
    timestamp = datetime.now(timezone.utc)
    run_id = f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:8]}"
    directory = (Path(report_dir) if report_dir is not None else default_report_dir(model_key)).resolve()
    return {"run_id": run_id, "timestamp": timestamp.isoformat(), "run_type": run_type,
            "report_dir": directory, "model_key": model_key, "model_name": model_name}


def report_paths(context: dict) -> dict[str, str]:
    return {"markdown": str(context["report_dir"] / f"{context['run_id']}.md"),
            "json": str(context["report_dir"] / f"{context['run_id']}.json")}


def pipeline_configuration(pipeline) -> dict:
    return {name: component.get_params(deep=False) for name, component in pipeline.named_steps.items()}


def run_payload(data, result, pipeline, fingerprints: dict, started: float) -> dict:
    from src.ML.metrics import SCORER_DEFINITIONS

    return {
        "status": "success", "elapsed_seconds": time.perf_counter() - started,
        "source_sha256": fingerprints, "training_samples": len(data.X_train),
        "cv_fold_ids": list(result.fold_ids), "cv_type": "PredefinedSplit",
        "scoring": SCORER_DEFINITIONS, "warnings": list(result.warnings), "versions": versions(),
        "random_seed": pipeline.named_steps["model"].get_params().get("random_state"),
        "model_configuration": pipeline_configuration(pipeline),
    }


def write_failure_report(context: dict, started: float, exc: Exception) -> None:
    try:
        write_report(context, {"status": "failure", "elapsed_seconds": time.perf_counter() - started,
                               "error": f"{type(exc).__name__}: {exc}", "versions": versions()})
    except Exception as report_error:
        if hasattr(exc, "add_note"):
            exc.add_note(f"Could not write failure report: {report_error}")


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
    document = {**payload, "run_id": context["run_id"], "timestamp_utc": context["timestamp"],
                "run_type": context["run_type"], "model_key": context.get("model_key"),
                "model_name": context.get("model_name", "ML")}
    json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = [f"# {document['model_name']} {context['run_type']} run", "", f"- Run ID: `{context['run_id']}`", f"- Timestamp (UTC): {context['timestamp']}", f"- Status: {document.get('status', 'unknown')}", "", "## Summary", "", "```json", json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str), "```", ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path

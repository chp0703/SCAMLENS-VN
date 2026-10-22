"""Run the approved final-test benchmark for Logistic Regression and SVM."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import uuid

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.ML.artifacts import load_artifact
from src.ML.approved_models import load_approved_artifact
from src.ML.data_utils import load_ml_data

from evaluation.bootstrap import (
    DEFAULT_BOOTSTRAP_REPLICATES,
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_RANDOM_SEED,
    bootstrap_metric_intervals,
    paired_bootstrap_metric_differences,
)
from evaluation.metrics import METRIC_NAMES, EvaluationMetrics, score_predictions


DEFAULT_DATA_DIR = BACKEND_DIR / "data" / "splits" / "ml"
DEFAULT_MANIFEST = BACKEND_DIR / "data" / "splits" / "manifest.json"
DEFAULT_REPORT_DIR = BACKEND_DIR / "experiments" / "benchmark"


def _as_dict(result: EvaluationMetrics) -> dict:
    return {
        "sample_count": result.sample_count,
        "metrics": asdict(result.values),
        "confusion": asdict(result.confusion),
    }


def _ci_dict(intervals: dict) -> dict:
    return {name: asdict(interval) for name, interval in intervals.items()}


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _test_ids_hash(ids: tuple[str, ...]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _model_markdown(name: str, result: dict, intervals: dict) -> list[str]:
    confusion = result["confusion"]
    lines = [f"### {name}", "", "| Metric | Estimate | 95% Bootstrap CI |", "|---|---:|---:|"]
    for metric, label in (
        ("accuracy", "Accuracy"),
        ("precision_scam", "Precision (Scam)"),
        ("recall_scam", "Recall (Scam)"),
        ("f1_scam", "F1 (Scam)"),
    ):
        interval = intervals[metric]
        lines.append(
            f"| {label} | {_format_percent(result['metrics'][metric])} | "
            f"[{_format_percent(interval['lower'])}, {_format_percent(interval['upper'])}] |"
        )
    lines.extend([
        "", "| | Predicted Ham | Predicted Scam |", "|---|---:|---:|",
        f"| Actual Ham | {confusion['tn']} | {confusion['fp']} |",
        f"| Actual Scam | {confusion['fn']} | {confusion['tp']} |",
        "", f"- False Positive (FP): {confusion['fp']}",
        f"- False Negative (FN): {confusion['fn']}", "",
    ])
    return lines


def _write_reports(payload: dict, report_dir: Path) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    run_id = payload["run_id"]
    json_path = report_dir / f"{run_id}.json"
    markdown_path = report_dir / f"{run_id}.md"
    payload["report_paths"] = {"json": str(json_path), "markdown": str(markdown_path)}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lr = payload["models"]["logistic_regression"]
    svm = payload["models"]["svm"]
    lines = [
        "# Logistic Regression vs Support Vector Machine Benchmark", "",
        f"- Status: {payload['status']}", f"- Test samples: {payload['test']['sample_count']}",
        f"- Bootstrap replicates: {payload['bootstrap']['replicates']}",
        f"- Confidence level: {payload['bootstrap']['confidence_level']:.0%}",
        "- Positive label: Scam (1)", "", "## Final test results", "",
        "| Model | Accuracy (%) | Precision (%) | Recall (%) | F1-Score (%) | 95% Bootstrap CI |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, result in (("Logistic Regression", lr), ("Support Vector Machine", svm)):
        f1_ci = result["bootstrap"]["f1_scam"]
        lines.append(
            f"| {name} | {_format_percent(result['metrics']['accuracy'])} | "
            f"{_format_percent(result['metrics']['precision_scam'])} | "
            f"{_format_percent(result['metrics']['recall_scam'])} | "
            f"{_format_percent(result['metrics']['f1_scam'])} | "
            f"[{_format_percent(f1_ci['lower'])}, {_format_percent(f1_ci['upper'])}] |"
        )
    lines.extend(["", "## Confusion matrices", ""])
    lines.extend(_model_markdown("Logistic Regression", lr, lr["bootstrap"]))
    lines.extend(_model_markdown("Support Vector Machine", svm, svm["bootstrap"]))
    lines.extend(["## Paired comparison", "", "Difference is defined as Logistic Regression - Support Vector Machine.", ""])
    lines.extend(["| Metric | Difference | 95% Bootstrap CI |", "|---|---:|---:|"])
    for metric in METRIC_NAMES:
        difference = payload["paired_comparison"][metric]
        lines.append(
            f"| {metric} | {_format_percent(difference['difference_estimate'])} | "
            f"[{_format_percent(difference['lower'])}, {_format_percent(difference['upper'])}] |"
        )
    lines.extend([
        "", "## Protocol", "", "- Test data was not used for tuning or threshold selection.",
        "- Bootstrap samples with a missing class were retained and scored with `zero_division=0`.",
        "- The source label `1` includes the dataset's spam/scam category; it is not necessarily scam-only.", "",
    ])
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path


def run_benchmark(
    *,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    manifest_path: str | Path = DEFAULT_MANIFEST,
    lr_artifact_dir: str | Path | None = None,
    svm_artifact_dir: str | Path | None = None,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    n_bootstrap: int = DEFAULT_BOOTSTRAP_REPLICATES,
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    seed: int = DEFAULT_RANDOM_SEED,
    confirm_final_test: bool = False,
) -> dict:
    if not confirm_final_test:
        raise PermissionError("Final test is locked; pass --confirm-final-test after leader approval")
    data_dir = Path(data_dir)
    manifest_path = Path(manifest_path)
    if (lr_artifact_dir is None) != (svm_artifact_dir is None):
        raise ValueError("Provide both explicit artifact directories or use both pinned shared models")
    data = load_ml_data(data_dir=data_dir, manifest_path=manifest_path)
    if lr_artifact_dir is None:
        lr_model, lr_metadata = load_approved_artifact("logistic_regression")
        svm_model, svm_metadata = load_approved_artifact("svm")
        artifact_source = "models.lock.json"
    else:
        lr_model, lr_metadata = load_artifact(Path(lr_artifact_dir))
        svm_model, svm_metadata = load_artifact(Path(svm_artifact_dir))
        artifact_source = "explicit_directories"
    lr_predictions = lr_model.predict(data.X_test)
    svm_predictions = svm_model.predict(data.X_test)
    lr_result = score_predictions(data.y_test, lr_predictions)
    svm_result = score_predictions(data.y_test, svm_predictions)
    lr_intervals = bootstrap_metric_intervals(data.y_test, lr_predictions, n_bootstrap=n_bootstrap, confidence_level=confidence_level, seed=seed)
    svm_intervals = bootstrap_metric_intervals(data.y_test, svm_predictions, n_bootstrap=n_bootstrap, confidence_level=confidence_level, seed=seed)
    paired = paired_bootstrap_metric_differences(data.y_test, lr_predictions, svm_predictions, n_bootstrap=n_bootstrap, confidence_level=confidence_level, seed=seed)
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:8]}"
    payload = {
        "status": "success",
        "run_id": run_id,
        "run_type": "final_benchmark",
        "final_test_confirmed": True,
        "artifact_source": artifact_source,
        "test": {
            "data_dir": str(data_dir.resolve()),
            "manifest": str(manifest_path.resolve()),
            "file_sha256": _sha256(data_dir / "test.csv"),
            "test_ids_sha256": _test_ids_hash(data.test_message_ids),
            "sample_count": len(data.y_test),
            "label_mapping": {"0": "Ham", "1": "Scam"},
        },
        "bootstrap": {"method": "percentile", "replicates": n_bootstrap, "confidence_level": confidence_level, "seed": seed},
        "models": {
            "logistic_regression": {**_as_dict(lr_result), "bootstrap": _ci_dict(lr_intervals), "artifact": lr_metadata},
            "svm": {**_as_dict(svm_result), "bootstrap": _ci_dict(svm_intervals), "artifact": svm_metadata},
        },
        "paired_comparison": {"difference_definition": "logistic_regression - svm", **_ci_dict(paired)},
    }
    json_path, markdown_path = _write_reports(payload, Path(report_dir))
    payload["report_paths"] = {"json": str(json_path), "markdown": str(markdown_path)}
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-final-test", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--lr-artifact-dir", type=Path, help="Local experiment override; requires --svm-artifact-dir")
    parser.add_argument("--svm-artifact-dir", type=Path, help="Local experiment override; requires --lr-artifact-dir")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--bootstrap-replicates", type=int, default=DEFAULT_BOOTSTRAP_REPLICATES)
    parser.add_argument("--confidence-level", type=float, default=DEFAULT_CONFIDENCE_LEVEL)
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    args = parser.parse_args(argv)
    try:
        payload = run_benchmark(
            data_dir=args.data_dir, manifest_path=args.manifest,
            lr_artifact_dir=args.lr_artifact_dir, svm_artifact_dir=args.svm_artifact_dir,
            report_dir=args.report_dir, n_bootstrap=args.bootstrap_replicates,
            confidence_level=args.confidence_level, seed=args.seed,
            confirm_final_test=args.confirm_final_test,
        )
    except Exception as exc:
        print(f"Benchmark failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"Benchmark completed on {payload['test']['sample_count']} test samples")
    for model_name, result in payload["models"].items():
        print(f"{model_name}: F1 Scam={_format_percent(result['metrics']['f1_scam'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

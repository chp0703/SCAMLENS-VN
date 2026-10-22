"""Evaluate Linear SVM on the shared training folds only."""

import argparse
from pathlib import Path
import sys
import time

from sklearn.model_selection import cross_validate

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ML.config import ModelConfig, load_model_config
from src.ML.cv import BaselineResult, evaluate_baseline as evaluate_cv, metric_summary
from src.ML.data_utils import MLData, load_ml_data
from src.ML.experiment_reporting import (
    new_run_context, run_payload, source_fingerprints, write_failure_report, write_report,
)
from src.ML.metrics import METRIC_LABELS, SCORING


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data/splits/ml"


def evaluate_baseline(data: MLData, config: ModelConfig | None = None) -> BaselineResult:
    config = config or load_model_config("svm")
    return evaluate_cv(data, config.build_pipeline(), cross_validate_fn=cross_validate)


def run_baseline(data_dir=None, manifest_path=None, report_dir=None, config_path=None) -> BaselineResult:
    context = new_run_context("baseline", report_dir, model_key="svm", model_name="Support Vector Machine")
    started = time.perf_counter()
    try:
        config = load_model_config("svm", config_path)
        data = load_ml_data(data_dir=data_dir, manifest_path=manifest_path)
        result = evaluate_baseline(data, config)
        payload = run_payload(data, result, config.build_pipeline(),
                              source_fingerprints(data_dir, DEFAULT_DATA_DIR), started)
        write_report(context, {**payload, "metrics": metric_summary(result)})
        return result
    except Exception as exc:
        write_failure_report(context, started, exc)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_baseline(args.data_dir, args.manifest, args.report_dir, args.config)
    except Exception as exc:
        print(f"SVM baseline failed: {exc}", file=sys.stderr)
        return 1
    print(f"SVM baseline: {len(result.fold_ids)} predefined CV folds")
    for metric in SCORING:
        print(f"{METRIC_LABELS[metric]}: {result.means[metric]:.4f} +/- {result.standard_deviations[metric]:.4f}")
    if result.warnings:
        print("Warnings:\n" + "\n".join(result.warnings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

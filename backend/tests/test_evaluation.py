"""Tests for shared final-test evaluation utilities."""

from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.bootstrap import (  # noqa: E402
    bootstrap_metric_intervals,
    paired_bootstrap_metric_differences,
)
from evaluation.benchmark import run_benchmark  # noqa: E402
from evaluation.metrics import score_predictions  # noqa: E402


class MetricsTests(unittest.TestCase):
    def test_metrics_and_confusion_counts(self):
        result = score_predictions([0, 0, 1, 1], [0, 1, 0, 1])
        self.assertEqual(result.sample_count, 4)
        self.assertEqual(result.confusion.tn, 1)
        self.assertEqual(result.confusion.fp, 1)
        self.assertEqual(result.confusion.fn, 1)
        self.assertEqual(result.confusion.tp, 1)
        self.assertAlmostEqual(result.values.accuracy, 0.5)
        self.assertAlmostEqual(result.values.precision_scam, 0.5)
        self.assertAlmostEqual(result.values.recall_scam, 0.5)
        self.assertAlmostEqual(result.values.f1_scam, 0.5)

    def test_zero_division_is_defined(self):
        result = score_predictions([0, 0], [0, 0])
        self.assertEqual(result.values.precision_scam, 0.0)
        self.assertEqual(result.values.recall_scam, 0.0)
        self.assertEqual(result.values.f1_scam, 0.0)

    def test_invalid_labels_and_shapes_are_rejected(self):
        with self.assertRaises(ValueError):
            score_predictions([], [])
        with self.assertRaises(ValueError):
            score_predictions([0], [0, 1])
        with self.assertRaises(ValueError):
            score_predictions([0, 2], [0, 1])
        with self.assertRaises(ValueError):
            score_predictions([[0]], [[0]])


class BootstrapTests(unittest.TestCase):
    def test_seed_is_reproducible_and_intervals_are_bounded(self):
        args = ([0, 0, 1, 1], [0, 1, 0, 1])
        first = bootstrap_metric_intervals(*args, n_bootstrap=20, seed=42)
        second = bootstrap_metric_intervals(*args, n_bootstrap=20, seed=42)
        self.assertEqual(first, second)
        for interval in first.values():
            self.assertEqual(interval.replicates, 20)
            self.assertGreaterEqual(interval.lower, 0.0)
            self.assertLessEqual(interval.upper, 1.0)

    def test_invalid_options_are_rejected(self):
        with self.assertRaises(ValueError):
            bootstrap_metric_intervals([0, 1], [0, 1], n_bootstrap=1)
        with self.assertRaises(ValueError):
            bootstrap_metric_intervals([0, 1], [0, 1], confidence_level=1)

    def test_paired_identical_predictions_have_zero_difference(self):
        result = paired_bootstrap_metric_differences(
            [0, 0, 1, 1], [0, 1, 0, 1], [0, 1, 0, 1], n_bootstrap=20
        )
        for difference in result.values():
            self.assertEqual(difference.difference_estimate, 0.0)
            self.assertEqual(difference.lower, 0.0)
            self.assertEqual(difference.upper, 0.0)

    def test_paired_predictions_must_have_matching_lengths(self):
        with self.assertRaises(ValueError):
            paired_bootstrap_metric_differences([0, 1], [0, 1], [0])


class BenchmarkTests(unittest.TestCase):
    def test_final_test_requires_explicit_confirmation_before_loading_data(self):
        with patch("evaluation.benchmark.load_ml_data") as loader:
            with self.assertRaises(PermissionError):
                run_benchmark(confirm_final_test=False)
        loader.assert_not_called()

    def test_benchmark_writes_json_and_markdown_with_shared_test_data(self):
        data = SimpleNamespace(
            X_test=["ham", "scam", "other", "urgent"],
            y_test=[0, 1, 0, 1],
            test_message_ids=("a", "b", "c", "d"),
        )

        class FakeModel:
            def __init__(self, predictions):
                self.predictions = predictions
                self.received = None

            def predict(self, texts):
                self.received = texts
                return self.predictions

        lr = FakeModel([0, 1, 1, 1])
        svm = FakeModel([0, 1, 0, 1])
        with tempfile.TemporaryDirectory() as directory:
            with patch("evaluation.benchmark.load_ml_data", return_value=data), patch(
                "evaluation.benchmark.load_approved_artifact",
                side_effect=[(lr, {"run_id": "lr"}), (svm, {"run_id": "svm"})],
            ):
                payload = run_benchmark(
                    data_dir=directory,
                    manifest_path=Path(directory) / "manifest.json",
                    report_dir=directory,
                    n_bootstrap=20,
                    confirm_final_test=True,
                )
            self.assertIs(lr.received, data.X_test)
            self.assertIs(svm.received, data.X_test)
            self.assertEqual(payload["test"]["sample_count"], 4)
            self.assertEqual(payload["bootstrap"]["replicates"], 20)
            self.assertEqual(payload["artifact_source"], "models.lock.json")
            self.assertTrue(Path(payload["report_paths"]["json"]).is_file())
            self.assertTrue(Path(payload["report_paths"]["markdown"]).is_file())

    def test_mixing_local_and_shared_models_is_rejected_before_loading_data(self):
        with patch("evaluation.benchmark.load_ml_data") as loader:
            with self.assertRaisesRegex(ValueError, "both"):
                run_benchmark(lr_artifact_dir="local-lr", confirm_final_test=True)
        loader.assert_not_called()

    def test_explicit_local_override_loads_both_directories(self):
        data = SimpleNamespace(X_test=["ham", "scam"], y_test=[0, 1], test_message_ids=("a", "b"))
        model = SimpleNamespace(predict=lambda texts: [0, 1])
        with tempfile.TemporaryDirectory() as directory:
            with patch("evaluation.benchmark.load_ml_data", return_value=data), patch(
                "evaluation.benchmark.load_artifact", return_value=(model, {"run_id": "local"})
            ) as local_loader, patch("evaluation.benchmark.load_approved_artifact") as shared_loader:
                payload = run_benchmark(
                    data_dir=directory, manifest_path=Path(directory) / "manifest.json",
                    lr_artifact_dir="local-lr", svm_artifact_dir="local-svm",
                    report_dir=directory, n_bootstrap=2, confirm_final_test=True,
                )
        self.assertEqual(payload["artifact_source"], "explicit_directories")
        self.assertEqual([call.args[0] for call in local_loader.call_args_list], [Path("local-lr"), Path("local-svm")])
        shared_loader.assert_not_called()


if __name__ == "__main__":
    unittest.main()

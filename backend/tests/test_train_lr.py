"""Focused tests for Logistic Regression baseline CV evaluation."""

from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from src.ML.data_utils import MLData, build_predefined_split
from src.ML.train_lr import evaluate_baseline, format_baseline_result, run_baseline


def synthetic_data() -> MLData:
    """Two valid predefined folds with one Ham and one Scam each."""
    texts = ["normal greeting", "urgent prize", "meeting schedule", "claim bonus"]
    labels = np.asarray([0, 1, 0, 1])
    folds = np.asarray([0, 0, 1, 1])
    return MLData(
        X_train=texts,
        y_train=labels,
        X_test=["unused test message"],
        y_test=np.asarray([1]),
        train_message_ids=("a", "b", "c", "d"),
        test_message_ids=("test",),
        fold_ids=folds,
        cv=build_predefined_split(folds),
    )


class LogisticRegressionBaselineTests(unittest.TestCase):
    def test_evaluation_uses_predefined_split_and_returns_scam_metrics(self):
        data = synthetic_data()
        with patch("src.ML.train_lr.cross_validate") as cross_validate_mock:
            cross_validate_mock.return_value = {
                "test_f1_scam": np.asarray([0.5, 1.0]),
                "test_precision_scam": np.asarray([0.4, 1.0]),
                "test_recall_scam": np.asarray([2 / 3, 1.0]),
            }
            result = evaluate_baseline(data)

        kwargs = cross_validate_mock.call_args.kwargs
        self.assertIs(kwargs["cv"], data.cv)
        self.assertEqual(cross_validate_mock.call_args.args[1], data.X_train)
        self.assertTrue(np.array_equal(cross_validate_mock.call_args.args[2], data.y_train))
        self.assertTrue(all(argument is not data.X_test for argument in cross_validate_mock.call_args.args))
        self.assertEqual(result.fold_ids, (0, 1))
        self.assertEqual(result.scores["f1_scam"], (0.5, 1.0))
        self.assertAlmostEqual(result.means["precision_scam"], 0.7)
        self.assertAlmostEqual(result.standard_deviations["recall_scam"], 1 / 6)
        self.assertIn("Scam, pos_label=1", format_baseline_result(result))

    def test_run_baseline_loads_data_without_using_test_values(self):
        data = synthetic_data()
        isolated = replace(data, X_test=[None], y_test=np.asarray([99]))
        with patch("src.ML.train_lr.load_ml_data", return_value=isolated) as loader:
            result = run_baseline()
        loader.assert_called_once_with(data_dir=None, manifest_path=None)
        self.assertEqual(len(result.fold_ids), 2)
        self.assertEqual(set(result.scores), {"f1_scam", "precision_scam", "recall_scam"})


if __name__ == "__main__":
    unittest.main()

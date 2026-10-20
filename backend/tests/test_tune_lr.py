"""Focused tests for LR GridSearchCV tuning and local artifacts."""

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import joblib
import numpy as np

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from src.ML.data_utils import MLData, build_predefined_split
from src.ML.metrics import SCORING as SHARED_SCORING
from src.ML.tune_lr import PARAM_GRID, SCORING, save_best_artifact, run_tuning, tune_data


def synthetic_data() -> MLData:
    texts = ["normal greeting", "claim urgent prize", "meeting schedule", "claim bonus now"]
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


class LogisticRegressionTuningTests(unittest.TestCase):
    def test_uses_exact_grid_predefined_split_and_scam_refit_metrics(self):
        data = synthetic_data()
        result = tune_data(data)
        self.assertEqual(result.search.param_grid, PARAM_GRID)
        self.assertIs(result.search.cv, data.cv)
        self.assertEqual(result.search.refit, "f1_scam")
        self.assertEqual(set(result.search.scoring), {"f1_scam", "precision_scam", "recall_scam"})
        self.assertEqual(result.candidate_count, 10)
        self.assertEqual(result.cv_fit_count, 20)
        self.assertEqual(set(result.per_fold_scores), {"f1_scam", "precision_scam", "recall_scam"})
        self.assertEqual(len(result.per_fold_scores["f1_scam"]), 2)
        self.assertEqual(result.best_estimator.named_steps.keys(), {"tfidf", "model"})

    def test_run_tuning_does_not_use_test_values(self):
        data = synthetic_data()
        isolated = replace(data, X_test=[None], y_test=np.asarray([99]))
        with patch("src.ML.tune_lr.load_ml_data", return_value=isolated) as loader:
            with tempfile.TemporaryDirectory() as directory:
                result = run_tuning(save_artifact=False, report_dir=directory)
        loader.assert_called_once_with(data_dir=None, manifest_path=None)
        self.assertEqual(result.candidate_count, 10)

    def test_artifact_metadata_reload_and_prediction(self):
        data = synthetic_data()
        result = tune_data(data)
        with tempfile.TemporaryDirectory() as directory:
            artifact = save_best_artifact(result, data, directory, {"train.csv": "abc", "cv_folds.csv": "def"}, "run-123", {"json": "report.json"})
            self.assertTrue(artifact.model_path.is_file())
            self.assertTrue(artifact.metadata_path.is_file())
            self.assertEqual(len(artifact.smoke_predictions), 2)
            self.assertEqual(len(joblib.load(artifact.model_path).predict(["hello"])), 1)
            metadata = json.loads(artifact.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["selection_metric"], "f1_scam")
            self.assertEqual(metadata["source_sha256"]["train.csv"], "abc")
            self.assertEqual(metadata["run_id"], "run-123")
            self.assertEqual(metadata["report_paths"]["json"], "report.json")
            self.assertNotIn("unused test message", artifact.metadata_path.read_text(encoding="utf-8"))

    def test_tuning_report_contains_all_cv_candidates_and_shared_scorers(self):
        self.assertIs(SCORING, SHARED_SCORING)
        with tempfile.TemporaryDirectory() as directory:
            run_tuning(save_artifact=False, report_dir=directory)
            payload = json.loads(next(Path(directory).glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "success")
            self.assertEqual(len(payload["candidates"]), 10)
            self.assertEqual(payload["selection_metric"], "f1_scam")

    def test_failed_tuning_writes_failure_report(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("src.ML.tune_lr.load_ml_data", side_effect=RuntimeError("unavailable")):
                with self.assertRaisesRegex(RuntimeError, "unavailable"):
                    run_tuning(report_dir=directory)
            payload = json.loads(next(Path(directory).glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "failure")
            self.assertNotIn("selected_cv_metrics", payload)

    def test_fit_failure_propagates_clearly(self):
        data = synthetic_data()
        failing_search = MagicMock()
        failing_search.fit.side_effect = RuntimeError("fit failed")
        with patch("src.ML.tune_lr.GridSearchCV", return_value=failing_search):
            with self.assertRaisesRegex(RuntimeError, "fit failed"):
                tune_data(data)


if __name__ == "__main__":
    unittest.main()

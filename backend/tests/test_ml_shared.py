"""Regression checks for config-driven CV and consistent artifact publication."""

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ML.artifacts import load_artifact, resolve_artifact_paths, save_artifact
from src.ML.config import load_model_config
from src.ML.data_utils import MLData, build_predefined_split
from src.ML.models.logistic_regression import build_lr_pipeline
from src.ML.train_svm import run_baseline
from src.ML.tune_svm import run_tuning, tune_data


def sample_data():
    folds = np.asarray([0, 0, 1, 1])
    return MLData(["normal greeting", "claim urgent prize", "meeting schedule", "claim bonus now"],
                  np.asarray([0, 1, 0, 1]), [None], np.asarray([99]),
                  ("a", "b", "c", "d"), ("unused",), folds, build_predefined_split(folds))


class ModelConfigTests(unittest.TestCase):
    def test_both_defaults_use_real_seed_and_shared_selection_metric(self):
        for model in ("logistic_regression", "svm"):
            config = load_model_config(model)
            self.assertEqual(config.build_pipeline().named_steps["model"].random_state, 42)
            self.assertEqual(config.primary_metric, "f1_scam")
            self.assertEqual(len(config.param_grid["model__C"]), 5)

    def test_invalid_or_ignored_settings_fail_before_training(self):
        valid = yaml.safe_load(load_model_config("svm").path.read_text(encoding="utf-8"))
        invalid = [None, {**valid, "unused": True},
                   {**valid, "model": {"type": "LogisticRegression"}},
                   {**valid, "evaluation": {"primary_metric": "accuracy"}},
                   {**valid, "tuning": {"model__C": []}},
                   {**valid, "tuning": {"model__C": [-1]}},
                   {**valid, "tuning": {"model__missing": [1]}},
                   {**valid, "model": {"type": "LinearSVC", "params": {"missing": True}}}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "svm.yaml"
            for document in invalid:
                with self.subTest(document=document):
                    path.write_text(yaml.safe_dump(document), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_model_config("svm", path)

    def test_yaml_ngram_lists_become_sklearn_tuples(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "svm.yaml"
            path.write_text(yaml.safe_dump({
                "model": {"type": "LinearSVC"}, "tfidf": {"analyzer": "char", "ngram_range": [2, 3]},
                "tuning": {"tfidf__ngram_range": [[2, 3], [3, 4]]},
                "evaluation": {"primary_metric": "recall_scam"},
            }), encoding="utf-8")
            config = load_model_config("svm", path)
            self.assertEqual(config.build_pipeline().named_steps["tfidf"].ngram_range, (2, 3))
            self.assertEqual(config.param_grid["tfidf__ngram_range"], [(2, 3), (3, 4)])

    def test_config_metric_controls_actual_grid_search_refit(self):
        config = replace(load_model_config("svm"), primary_metric="recall_scam",
                         param_grid={"model__C": [1]})
        result = tune_data(sample_data(), config)
        self.assertEqual(result.search.refit, "recall_scam")
        self.assertEqual(result.selection_metric, "recall_scam")


class ArtifactPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = sample_data()
        cls.model = build_lr_pipeline().fit(data.X_train, data.y_train)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.first = save_artifact(self.model, {"run_id": "old"}, self.root)
        self.pointer = (self.root / "current.json").read_bytes()

    def assert_previous_version_still_active(self):
        self.assertEqual((self.root / "current.json").read_bytes(), self.pointer)
        model, metadata = load_artifact(self.root)
        self.assertEqual(metadata["run_id"], "old")
        self.assertEqual(len(model.predict(["hello"])), 1)

    def test_new_version_keeps_previous_pair_immutable(self):
        previous = self.first.model_path.read_bytes(), self.first.metadata_path.read_bytes()
        second = save_artifact(self.model, {"run_id": "new"}, self.root)
        self.assertNotEqual(second.model_path, self.first.model_path)
        self.assertEqual(previous, (self.first.model_path.read_bytes(), self.first.metadata_path.read_bytes()))
        self.assertEqual(load_artifact(self.root)[1]["run_id"], "new")

    def test_metadata_write_failure_leaves_previous_pair_active(self):
        original = Path.write_text

        def fail_metadata(path, *args, **kwargs):
            if path.name == "metadata.json":
                raise OSError("metadata failed")
            return original(path, *args, **kwargs)

        with patch.object(Path, "write_text", fail_metadata):
            with self.assertRaisesRegex(OSError, "metadata failed"):
                save_artifact(self.model, {"run_id": "new"}, self.root)
        self.assert_previous_version_still_active()

    def test_pointer_update_failure_leaves_previous_pair_active(self):
        original = Path.replace

        def fail_pointer(path, target):
            if Path(target).name == "current.json":
                raise OSError("pointer failed")
            return original(path, target)

        with patch.object(Path, "replace", fail_pointer):
            with self.assertRaisesRegex(OSError, "pointer failed"):
                save_artifact(self.model, {"run_id": "new"}, self.root)
        self.assert_previous_version_still_active()

    def test_reload_failure_leaves_previous_pair_active(self):
        with patch("src.ML.artifacts.joblib.load", side_effect=ValueError("reload failed")):
            with self.assertRaisesRegex(ValueError, "reload failed"):
                save_artifact(self.model, {"run_id": "new"}, self.root)
        self.assert_previous_version_still_active()

    def test_existing_run_cannot_be_overwritten(self):
        with self.assertRaises(FileExistsError):
            save_artifact(self.model, {"run_id": "old"}, self.root)
        self.assert_previous_version_still_active()

    def test_tampered_metadata_is_rejected(self):
        self.first.metadata_path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "integrity"):
            resolve_artifact_paths(self.root)

    def test_legacy_pair_is_readable_and_preserved_by_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            joblib.dump(self.model, root / "model.joblib")
            (root / "metadata.json").write_text('{"legacy": true}', encoding="utf-8")
            previous = (root / "model.joblib").read_bytes()
            self.assertTrue(load_artifact(root)[1]["legacy"])
            save_artifact(self.model, {"run_id": "new"}, root)
            self.assertEqual((root / "model.joblib").read_bytes(), previous)
            self.assertEqual(load_artifact(root)[1]["run_id"], "new")


class SVMRunIntegrationTests(unittest.TestCase):
    def test_baseline_report_matches_actual_seed_and_model(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("src.ML.train_svm.load_ml_data", return_value=sample_data()):
                run_baseline(report_dir=directory)
            payload = json.loads(next(Path(directory).glob("*.json")).read_text(encoding="utf-8"))
            markdown = next(Path(directory).glob("*.md")).read_text(encoding="utf-8")
            self.assertEqual(payload["random_seed"], payload["model_configuration"]["model"]["random_state"])
            self.assertEqual(payload["random_seed"], 42)
            self.assertTrue(markdown.startswith("# Support Vector Machine baseline run"))

    def test_custom_config_report_paths_and_versioned_artifact_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "custom.yaml"
            config.write_text(yaml.safe_dump({
                "model": {"type": "LinearSVC", "params": {"random_state": 7}},
                "tuning": {"model__C": [1]},
                "evaluation": {"primary_metric": "recall_scam"},
            }), encoding="utf-8")
            with patch("src.ML.tune_svm.load_ml_data", return_value=sample_data()):
                search = run_tuning(report_dir=root / "reports", artifact_dir=root / "artifacts",
                                    config_path=config)
            model, metadata = load_artifact(root / "artifacts")
            self.assertEqual(search.refit, "recall_scam")
            self.assertEqual(model.named_steps["model"].random_state, 7)
            self.assertEqual(metadata["random_seed"], 7)
            self.assertTrue(Path(metadata["report_paths"]["json"]).is_file())
            payload = json.loads(Path(metadata["report_paths"]["json"]).read_text(encoding="utf-8"))
            self.assertEqual(payload["model_key"], "svm")
            self.assertEqual(len(payload["candidates"]), 1)
            self.assertEqual(payload["model_configuration"]["model"]["C"], search.best_params_["model__C"])


if __name__ == "__main__":
    unittest.main()

"""Regression checks for pinned artifacts, runtime and raw-text inference."""

from copy import deepcopy
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import patch

import joblib

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.preprocessing import RULES_VERSION
from src.ML.approved_models import (
    DEFAULT_DECISION_RULE, load_approved_artifact, predict_approved_texts, verify_shared_models,
)
from src.ML.models.logistic_regression import build_lr_pipeline


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ApprovedModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = build_lr_pipeline().fit(
            ["hello friend", "normal meeting", "claim prize", "urgent bonus"], [0, 0, 1, 1],
        )

    def setUp(self):
        temp_root = BACKEND / "tests/.tmp"
        temp_root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        with tempfile.NamedTemporaryFile(dir=BACKEND, prefix="model-lock-test-", suffix=".json", delete=False) as stream:
            self.lock_path = Path(stream.name)
        self.addCleanup(self.lock_path.unlink, missing_ok=True)
        self.model_path = self.root / "model.joblib"
        self.metadata_path = self.root / "metadata.json"
        joblib.dump(self.model, self.model_path)
        self.source = {"train.csv": "test-training-hash", "cv_folds.csv": "test-fold-hash"}
        self.metadata_path.write_text(json.dumps({"run_id": "frozen-run", "source_sha256": self.source}), encoding="utf-8")
        preprocessing = BACKEND / "app/services/preprocessing.py"
        self.document = {
            "schema_version": 1, "bundle_id": "test-bundle",
            "runtime": {
                "python_series": ".".join(platform.python_version_tuple()[:2]),
                "packages": {"scikit-learn": version("scikit-learn")},
            },
            "preprocessing": {
                "path": "app/services/preprocessing.py", "rules_version": RULES_VERSION,
                "sha256_lf": hashlib.sha256(preprocessing.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            },
            "training_source_sha256": self.source,
            "models": {"logistic_regression": {
                "artifact_dir": self.root.relative_to(BACKEND).as_posix(), "run_id": "frozen-run",
                "model_sha256": digest(self.model_path), "metadata_sha256": digest(self.metadata_path),
                "decision_rule": deepcopy(DEFAULT_DECISION_RULE),
            }},
        }
        self.write_lock()

    def write_lock(self):
        self.lock_path.write_text(json.dumps(self.document), encoding="utf-8")

    def assert_rejected_before_deserialization(self, message, error=ValueError):
        with patch("src.ML.approved_models.joblib.load") as loader:
            with self.assertRaisesRegex(error, message):
                load_approved_artifact("logistic_regression", self.lock_path)
        loader.assert_not_called()

    def test_pinned_pipeline_ignores_local_current_pointer(self):
        (self.root / "current.json").write_text('{"run_id":"different-local-run"}', encoding="utf-8")
        model, metadata = load_approved_artifact("logistic_regression", self.lock_path)
        self.assertEqual(model.predict(["hello friend"]).tolist(), self.model.predict(["hello friend"]).tolist())
        self.assertEqual(metadata["run_id"], "frozen-run")
        self.assertEqual(metadata["shared_bundle_id"], "test-bundle")

    def test_tampered_model_or_metadata_never_reaches_joblib(self):
        for path in (self.model_path, self.metadata_path):
            with self.subTest(path=path):
                original = path.read_bytes()
                path.write_bytes(original + b"changed")
                self.assert_rejected_before_deserialization("SHA-256")
                path.write_bytes(original)

    def test_missing_model_and_unresolved_lfs_pointer_have_actionable_errors(self):
        self.model_path.unlink()
        self.assert_rejected_before_deserialization("git lfs pull", FileNotFoundError)
        self.model_path.write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 10\n")
        self.assert_rejected_before_deserialization("git lfs pull")

    def test_runtime_mismatch_is_rejected(self):
        self.document["runtime"]["packages"]["scikit-learn"] = "0.0.0"
        self.write_lock()
        self.assert_rejected_before_deserialization("scikit-learn==0.0.0", RuntimeError)
        self.document["runtime"]["python_series"] = "0.0"
        self.write_lock()
        self.assert_rejected_before_deserialization("Python 0.0", RuntimeError)

    def test_preprocessing_change_is_rejected(self):
        self.document["preprocessing"]["sha256_lf"] = "0" * 64
        self.write_lock()
        self.assert_rejected_before_deserialization("SHA-256")

    def test_run_id_and_training_lineage_must_match_lock(self):
        self.document["models"]["logistic_regression"]["run_id"] = "another-run"
        self.write_lock()
        self.assert_rejected_before_deserialization("run_id")
        self.document["models"]["logistic_regression"]["run_id"] = "frozen-run"
        self.document["training_source_sha256"] = {"train.csv": "different"}
        self.write_lock()
        self.assert_rejected_before_deserialization("training data")

    def test_unknown_model_does_not_fall_back_to_local_artifact(self):
        with self.assertRaisesRegex(ValueError, "Unknown shared model"):
            load_approved_artifact("unknown", self.lock_path)

    def test_unimplemented_threshold_and_paths_outside_backend_are_rejected(self):
        self.document["models"]["logistic_regression"]["decision_rule"]["threshold"] = 0.5
        self.write_lock()
        self.assert_rejected_before_deserialization("decision rule")
        self.document["models"]["logistic_regression"]["decision_rule"] = DEFAULT_DECISION_RULE
        self.document["models"]["logistic_regression"]["artifact_dir"] = "../outside-backend"
        self.write_lock()
        self.assert_rejected_before_deserialization("inside the backend")

    def test_raw_text_inference_normalizes_entities_and_reports_score_kind(self):
        raw = ["  HELLO   https://example.com  "]
        result = predict_approved_texts("logistic_regression", raw, self.lock_path)
        self.assertEqual(result["labels"], self.model.predict(["hello [URL]"]).tolist())
        self.assertEqual(result["decision_scores"], self.model.decision_function(["hello [URL]"]).tolist())
        self.assertEqual(result["score_type"], "decision_function")

    def test_smoke_check_rejects_a_regression_even_with_valid_hashes(self):
        fixture = self.root / "smoke.json"
        expected = predict_approved_texts("logistic_regression", ["hello friend"], self.lock_path)
        fixture.write_text(json.dumps({"raw_texts": ["hello friend"], "models": {
            "logistic_regression": {"labels": [1 - expected["labels"][0]],
                                    "decision_scores": expected["decision_scores"]},
        }}), encoding="utf-8")
        self.document["smoke_test"] = {
            "path": fixture.relative_to(BACKEND).as_posix(), "sha256": digest(fixture),
            "score_absolute_tolerance": 1e-8,
        }
        self.write_lock()
        with self.assertRaisesRegex(ValueError, "regression predictions"):
            verify_shared_models(self.lock_path)


if __name__ == "__main__":
    unittest.main()

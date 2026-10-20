
"""Unit tests for the ScamLens Linear SVM pipeline."""

import unittest

from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.ML.models.svm import build_svm_pipeline
from src.ML.tune_svm import load_param_grid


class TestSVMPipeline(unittest.TestCase):

    def test_pipeline_structure(self):
        pipeline = build_svm_pipeline()

        self.assertIsInstance(pipeline, Pipeline)
        self.assertEqual(
            list(pipeline.named_steps),
            ["tfidf", "model"],
        )
        self.assertIsInstance(
            pipeline.named_steps["model"],
            LinearSVC,
        )

    def test_custom_parameters(self):
        pipeline = build_svm_pipeline(
            tfidf_params={"ngram_range": (1, 2)},
            model_params={
                "C": 10,
                "class_weight": "balanced",
            },
        )

        self.assertEqual(
            pipeline.named_steps["tfidf"].ngram_range,
            (1, 2),
        )
        self.assertEqual(
            pipeline.named_steps["model"].C,
            10,
        )
        self.assertEqual(
            pipeline.named_steps["model"].class_weight,
            "balanced",
        )

    def test_prediction(self):
        texts = [
            "nhan thuong truy cap link",
            "chuc mung trung thuong",
            "hop lop vao thu hai",
            "hen ban di an trua",
        ]
        labels = [1, 1, 0, 0]

        pipeline = build_svm_pipeline()
        pipeline.fit(texts, labels)
        predictions = pipeline.predict(texts)

        self.assertEqual(len(predictions), 4)
        self.assertTrue(
            set(predictions).issubset({0, 1})
        )

    def test_tuning_grid(self):
        grid = load_param_grid()

        self.assertEqual(
            grid["model__C"],
            [0.01, 0.1, 1, 10, 100],
        )
        self.assertEqual(
            grid["model__class_weight"],
            [None, "balanced"],
        )


if __name__ == "__main__":
    unittest.main()

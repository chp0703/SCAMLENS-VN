
"""Linear SVM pipeline for HAM/SCAM text classification."""

from collections.abc import Mapping
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


def build_svm_pipeline(
    tfidf_params: Mapping[str, Any] | None = None,
    model_params: Mapping[str, Any] | None = None,
) -> Pipeline:
    """Build an unfitted TF-IDF + LinearSVC pipeline."""
    vectorizer = TfidfVectorizer(**dict(tfidf_params or {}))
    classifier = LinearSVC(**dict(model_params or {}))

    return Pipeline([
        ("tfidf", vectorizer),
        ("model", classifier),
    ])
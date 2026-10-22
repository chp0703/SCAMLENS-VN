
"""Logistic Regression pipeline for HAM/SCAM text classification."""

from collections.abc import Mapping
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def build_lr_pipeline(
    tfidf_params: Mapping[str, Any] | None = None,
    model_params: Mapping[str, Any] | None = None,
) -> Pipeline:
    """Build a reusable TF-IDF + Logistic Regression pipeline.

    Args:
        tfidf_params: Optional TfidfVectorizer parameters.
        model_params: Optional LogisticRegression parameters.

    Returns:
        An unfitted sklearn Pipeline.
    """
    vectorizer = TfidfVectorizer(**dict(tfidf_params or {}))
    classifier = LogisticRegression(**dict(model_params or {}))

    return Pipeline([
        ("tfidf", vectorizer),
        ("model", classifier),
    ])



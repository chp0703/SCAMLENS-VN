"""Shared Scam-class scoring definitions for LR evaluation and tuning."""

from sklearn.metrics import f1_score, make_scorer, precision_score, recall_score


SCORING = {
    "f1_scam": make_scorer(f1_score, pos_label=1, zero_division=0),
    "precision_scam": make_scorer(precision_score, pos_label=1, zero_division=0),
    "recall_scam": make_scorer(recall_score, pos_label=1, zero_division=0),
}
METRICS = tuple(SCORING)
METRIC_LABELS = {
    "f1_scam": "F1 (Scam, pos_label=1)",
    "precision_scam": "Precision (Scam, pos_label=1)",
    "recall_scam": "Recall (Scam, pos_label=1)",
}
SCORER_DEFINITIONS = {
    "f1_scam": "f1_score(pos_label=1, zero_division=0)",
    "precision_scam": "precision_score(pos_label=1, zero_division=0)",
    "recall_scam": "recall_score(pos_label=1, zero_division=0)",
}

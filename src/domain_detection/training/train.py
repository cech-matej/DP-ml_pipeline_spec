"""Minimal model-centric training entry point.

This example deliberately does not calculate phase/cascade metrics. A training run
trains one classifier and records model-level metrics/lineage.
"""
from dataclasses import dataclass
from typing import Any

from sklearn.metrics import accuracy_score, precision_recall_fscore_support


@dataclass(frozen=True)
class TrainingResult:
    model: Any
    metrics: dict[str, float]


def train_classifier(estimator, X_train, y_train, X_test, y_test) -> TrainingResult:
    model = estimator.fit(X_train, y_train)
    predictions = model.predict(X_test)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, predictions, average="weighted", zero_division=0
    )
    return TrainingResult(
        model=model,
        metrics={
            "accuracy": float(accuracy_score(y_test, predictions)),
            "precision_weighted": float(precision),
            "recall_weighted": float(recall),
            "f1_weighted": float(f1),
        },
    )

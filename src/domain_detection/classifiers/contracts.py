from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClassifierPrediction:
    kind: str
    label: str | None = None
    scores: dict[str, float] | None = None
    score_name: str | None = None
    score: float | None = None


@dataclass(frozen=True)
class FeatureContribution:
    name: str
    value: Any
    contribution: float


@dataclass(frozen=True)
class LocalExplanation:
    method: str
    target: str | None
    base_value: float | None
    output_value: float | None
    features: tuple[FeatureContribution, ...]


class Classifier:
    def predict(self, features):
        raise NotImplementedError

    def explain(self, features, prediction: ClassifierPrediction) -> LocalExplanation:
        raise NotImplementedError

    def metadata(self) -> dict:
        raise NotImplementedError

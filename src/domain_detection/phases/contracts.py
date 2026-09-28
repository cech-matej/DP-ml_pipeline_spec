from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseInput:
    request_id: str
    facts: dict


@dataclass(frozen=True)
class ClassifierResult:
    classifier: str
    version: str
    prediction: object
    explanation: object


@dataclass(frozen=True)
class PhaseResult:
    request_id: str
    phase: str
    version: str
    classifiers: tuple[ClassifierResult, ...]

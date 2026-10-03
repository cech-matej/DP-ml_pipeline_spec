"""Transport-independent contracts for batched phase inference."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PhaseInput:
    domains: tuple[dict[str, Any], ...]
    include_explanations: bool = False


@dataclass(frozen=True)
class ClassifierResult:
    classifier: str
    version: str
    prediction: object
    explanation: object | None = None


@dataclass(frozen=True)
class DomainResult:
    domain_id: str
    classifiers: tuple[ClassifierResult, ...]


@dataclass(frozen=True)
class PhaseResult:
    phase: str
    version: str
    domains: tuple[DomainResult, ...]

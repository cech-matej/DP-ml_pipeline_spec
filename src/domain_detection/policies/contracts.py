from typing import Any, Protocol


class PhasePolicy(Protocol):
    def evaluate(self, classifier_results: list[dict[str, Any]]) -> str: ...

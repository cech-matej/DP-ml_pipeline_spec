"""Example phase-level rule policy."""
from typing import Any


def evaluate_rule_policy(results: list[dict[str, Any]], config: dict[str, Any]) -> str:
    """Evaluate simple ordered rules over classifier results.

    This policy chooses a phase-level label only. It does not decide what to collect
    next; orchestration remains outside the ML service.
    """
    for rule in config.get("rules", []):
        for result in results:
            prediction = result.get("prediction", {})
            if prediction.get("label") == rule.get("when_label"):
                return rule["output"]
    return config.get("otherwise", "uncertain")

"""Model-specific training-only outlier filtering."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OutlierReport:
    input_rows: int
    removed_rows: int
    remaining_rows: int
    policy_name: str


def apply_training_outlier_policy(X, policy: Any, *, estimator_factory=None):
    """Return filtered X plus an audit report; never mutates the caller's frame.

    `policy` is intentionally a plain mapping so YAML remains the source of truth.
    The detector is fitted only on the supplied training partition.
    """
    if not policy:
        return X.copy(), OutlierReport(len(X), 0, len(X), "none")
    if not policy.get("action", {}).get("remove", False):
        return X.copy(), OutlierReport(len(X), 0, len(X), policy["outlier_policy"]["name"])
    if policy["method"]["type"] != "isolation_forest":
        raise ValueError("example implementation supports isolation_forest only")
    from sklearn.ensemble import IsolationForest
    estimator = estimator_factory or IsolationForest
    detector = estimator(contamination=policy["method"]["contamination"], random_state=42)
    mask = detector.fit_predict(X) == 1
    remaining = X.loc[mask].copy()
    minimum = policy["minimum_training_rows"]
    if len(remaining) < minimum:
        raise ValueError(f"outlier policy would leave {len(remaining)} rows; minimum is {minimum}")
    return remaining, OutlierReport(len(X), int((~mask).sum()), len(remaining), policy["outlier_policy"]["name"])

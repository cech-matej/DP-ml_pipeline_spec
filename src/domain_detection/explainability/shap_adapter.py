"""SHAP adapter example for supported tree-based classifiers."""
from typing import Any

from domain_detection.classifiers.contracts import FeatureContribution, LocalExplanation


class ShapExplainer:
    def __init__(self, model):
        try:
            import shap
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("SHAP is required for ShapExplainer") from exc
        self._explainer = shap.TreeExplainer(model)

    def explain(self, feature_names: list[str], row, target_index: int | None = None) -> LocalExplanation:
        values = self._explainer.shap_values(row)
        base = self._explainer.expected_value
        if isinstance(values, list):
            index = 0 if target_index is None else target_index
            values = values[index]
            base = base[index]
        values = values[0] if getattr(values, "ndim", 1) > 1 else values
        base_value = float(base[0] if hasattr(base, "__len__") else base)
        return LocalExplanation(
            method="shap",
            target=str(target_index) if target_index is not None else None,
            base_value=base_value,
            output_value=None,
            features=tuple(
                FeatureContribution(name=name, value=row[name], contribution=float(value))
                for name, value in zip(feature_names, values)
            ),
        )

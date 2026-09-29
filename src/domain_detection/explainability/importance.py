"""Global feature-importance helpers."""


def native_gain(model) -> dict[str, float]:
    """Return native tree gain when the wrapped model exposes it."""
    if hasattr(model, "booster_"):
        booster = model.booster_
        names = booster.feature_name()
        gains = booster.feature_importance(importance_type="gain")
        return {name: float(gain) for name, gain in zip(names, gains)}
    if hasattr(model, "feature_importances_"):
        return {str(i): float(v) for i, v in enumerate(model.feature_importances_)}
    raise TypeError("model does not expose native feature importance")

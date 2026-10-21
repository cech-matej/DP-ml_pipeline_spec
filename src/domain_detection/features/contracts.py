from dataclasses import dataclass
from typing import Any

import numpy as np


class FeatureSchemaMismatch(ValueError):
    pass


@dataclass(frozen=True)
class FeatureVector:
    schema_name: str
    schema_version: int
    values: dict[str, Any]


class FeatureSchema:
    """Runtime schema loaded from the versioned feature-vector file.

    The schema file is the single source of truth for names/types. Extractors only
    calculate values and hand them to validate().
    """

    def __init__(self, name: str, version: int, features: list[dict]):
        self.name = name
        self.version = version
        self.features = {f["name"]: f for f in features}

    def validate(self, values: dict[str, Any]) -> FeatureVector:
        expected = set(self.features)
        actual = set(values)
        missing = expected - actual
        extra = actual - expected
        if missing or extra:
            raise FeatureSchemaMismatch(
                f"schema={self.name}-v{self.version} missing={sorted(missing)} extra={sorted(extra)}"
            )
        # Type validation is implemented centrally from the schema's `type` field.
        # Extractors never repeat those declarations.
        for name, spec in self.features.items():
            self._validate_type(name, values[name], spec["type"], spec.get("nullable", False))
        return FeatureVector(self.name, self.version, dict(values))

    @staticmethod
    def _validate_type(name: str, value: Any, dtype: str, nullable: bool) -> None:
        if value is None:
            if nullable:
                return
            raise FeatureSchemaMismatch(f"feature={name} is not nullable")
        checks = {
            "string": str,
            "int32": (int, np.int32),
            "int64": (int, np.int64),
            "float32": (float, int, np.float32),
            "float64": (float, int, np.float64),
            "bool": bool,
        }
        expected = checks.get(dtype)
        if expected is None:
            raise FeatureSchemaMismatch(f"unsupported feature type: {dtype}")
        if not isinstance(value, expected) or (dtype.startswith("int") and isinstance(value, bool)):
            raise FeatureSchemaMismatch(
                f"feature={name} expected_type={dtype} actual_type={type(value).__name__}"
            )

"""Transport contracts shared by HTTP, Kafka and future wrappers."""
from dataclasses import asdict, dataclass
from typing import Any, Protocol
import json

from domain_detection.phases.contracts import PhaseInput, PhaseResult


@dataclass(frozen=True)
class ServiceRequest:
    request_id: str
    phase: str
    phase_version: str
    facts: dict[str, Any]

    def to_phase_input(self) -> PhaseInput:
        return PhaseInput(request_id=self.request_id, facts=self.facts)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServiceRequest":
        return cls(
            request_id=str(data["request_id"]),
            phase=str(data["phase"]),
            phase_version=str(data["phase_version"]),
            facts=dict(data.get("facts", {})),
        )


@dataclass(frozen=True)
class ServiceResponse:
    request_id: str
    phase: str
    phase_version: str
    result: dict[str, Any]

    @classmethod
    def from_phase_result(cls, result: PhaseResult) -> "ServiceResponse":
        return cls(
            request_id=result.request_id,
            phase=result.phase,
            phase_version=result.version,
            result={
                "classifiers": [
                    {
                        "name": item.classifier,
                        "version": item.version,
                        "prediction": _jsonable(item.prediction),
                        "explanation": _jsonable(item.explanation),
                    }
                    for item in result.classifiers
                ]
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TransportWrapper(Protocol):
    """Wire-level wrapper. It owns serialization and delivery, not ML logic."""

    def start(self, handler) -> None: ...


def encode_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, separators=(",", ":"), default=_jsonable).encode("utf-8")


def decode_json(payload: bytes | str) -> dict[str, Any]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    return json.loads(payload)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if hasattr(value, "item"):
        return value.item()
    return value

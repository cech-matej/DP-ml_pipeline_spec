"""Wire contracts shared by interchangeable HTTP and Kafka wrappers."""
from dataclasses import asdict, dataclass
from typing import Any, Protocol
import json

from domain_detection.phases.contracts import PhaseInput, PhaseResult


@dataclass(frozen=True)
class ServiceRequest:
    domains: tuple[dict[str, Any], ...]
    include_explanations: bool = False

    def to_phase_input(self) -> PhaseInput:
        return PhaseInput(
            domains=self.domains,
            include_explanations=self.include_explanations,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServiceRequest":
        raw_domains = data.get("domains")

        if not isinstance(raw_domains, list) or not raw_domains:
            raise ValueError("'domains' must be a non-empty list")
        domains: list[dict[str, Any]] = []
        for domain in raw_domains:
            if not isinstance(domain, dict):
                raise ValueError("each item in 'domains' must be an object")
            if "domain_id" not in domain:
                raise ValueError("each domain must contain 'domain_id'")
            domains.append(dict(domain))
        ids = [str(domain["domain_id"]) for domain in domains]
        if len(ids) != len(set(ids)):
            raise ValueError("'domain_id' values must be unique within a request")
        return cls(
            domains=tuple(domains),
            include_explanations=bool(data.get("include_explanations", False)),
        )


@dataclass(frozen=True)
class ServiceResponse:
    phase: str
    phase_version: str
    result: dict[str, Any]

    @classmethod
    def from_phase_result(cls, result: PhaseResult) -> "ServiceResponse":
        return cls(
            phase=result.phase,
            phase_version=result.version,
            result={
                "domains": [
                    {
                        "domain_id": domain.domain_id,
                        "classifiers": [
                            {
                                "name": item.classifier,
                                "version": item.version,
                                "prediction": _jsonable(item.prediction),
                                **({"explanation": _jsonable(item.explanation)} if item.explanation is not None else {}),
                            }
                            for item in domain.classifiers
                        ],
                    }
                    for domain in result.domains
                ]
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TransportWrapper(Protocol):
    """Wire-level wrapper. It owns serialization/delivery, not ML logic."""

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

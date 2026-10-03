"""Select an interchangeable transport wrapper from configuration."""
from .http import create_app
from .kafka import KafkaWrapper


def build_transport(phase, config: dict):
    transport = config["transport"]
    kind = transport["type"]
    if kind == "http":
        return create_app(phase)
    if kind == "kafka":
        return KafkaWrapper(phase, **transport["kafka"])
    raise ValueError(f"unsupported transport type: {kind}")

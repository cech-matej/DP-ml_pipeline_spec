"""Select a wire wrapper from configuration."""
from .http import create_app
from .kafka import KafkaWrapper


def build_transport(phase, config: dict):
    transport = config.get("type", "http").lower()
    if transport == "http":
        return create_app(phase)
    if transport == "kafka":
        kafka = config["kafka"]
        return KafkaWrapper(
            phase,
            bootstrap_servers=kafka["bootstrap_servers"],
            input_topic=kafka["input_topic"],
            output_topic=kafka["output_topic"],
            group_id=kafka["group_id"],
            client_id=kafka.get("client_id"),
        )
    raise ValueError(f"unsupported transport wrapper: {transport}")

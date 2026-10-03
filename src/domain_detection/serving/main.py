"""Example entrypoint selection for a phase transport wrapper."""
from .factory import build_transport


def start_transport(phase, config: dict):
    """Build the configured wrapper; deployment decides HTTP vs Kafka."""
    return build_transport(phase, config)

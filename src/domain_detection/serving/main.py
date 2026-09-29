"""Example entry point showing wrapper selection.

The actual application/container can load a configured PhaseRunner and then choose
HTTP or Kafka without changing the phase implementation.
"""

from .factory import build_transport


def build_service(phase, transport_config: dict):
    return build_transport(phase, transport_config)

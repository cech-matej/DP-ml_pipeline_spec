"""Small application runner shared by all transport wrappers."""
from domain_detection.phases.contracts import PhaseInput
from .contracts import ServiceRequest, ServiceResponse


class ServiceHandler:
    def __init__(self, phase):
        self.phase = phase

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        if request.phase != self.phase.name:
            raise ValueError(f"request phase={request.phase!r} does not match service phase={self.phase.name!r}")
        result = self.phase.run(request.to_phase_input())
        return ServiceResponse.from_phase_result(result)

"""Transport-independent request handler shared by all wrappers."""
from domain_detection.serving.contracts import ServiceRequest, ServiceResponse


class ServiceHandler:
    def __init__(self, phase):
        self.phase = phase

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        result = self.phase.run(request.to_phase_input())
        return ServiceResponse.from_phase_result(result)

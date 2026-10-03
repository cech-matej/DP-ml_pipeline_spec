"""Transport-independent request handler shared by all wrappers."""
from domain_detection.serving.contracts import ServiceRequest, ServiceResponse


class ServiceHandler:
    def __init__(self, phase):
        self.phase = phase

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        if request.phase != self.phase.name:
            raise ValueError(
                f"request phase={request.phase!r} does not match service phase={self.phase.name!r}"
            )
        if request.phase_version != str(self.phase.version):
            raise ValueError(
                f"request phase_version={request.phase_version!r} does not match service phase="
                f"{self.phase.version!r}"
            )
        result = self.phase.run(request.to_phase_input())
        return ServiceResponse.from_phase_result(result)

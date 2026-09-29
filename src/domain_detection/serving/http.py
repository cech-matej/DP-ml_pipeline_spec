"""Standalone HTTP wrapper.

The wrapper contains no classifier/feature logic. Swap this wrapper for Kafka without
changing PhaseRunner, extractors or classifiers.
"""
from .contracts import ServiceRequest, encode_json, decode_json
from .runner import ServiceHandler

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import Response
except ImportError as exc:  # pragma: no cover - optional dependency
    FastAPI = None
    _FASTAPI_IMPORT_ERROR = exc


def create_app(phase):
    if FastAPI is None:
        raise RuntimeError("HTTP serving requires the 'serving' optional dependencies") from _FASTAPI_IMPORT_ERROR
    handler = ServiceHandler(phase)
    app = FastAPI(title=f"{phase.name} phase")

    @app.get("/health")
    def health():
        return {"status": "ok", "phase": phase.name, "version": phase.version}

    @app.post("/predict")
    async def predict(payload: dict):
        try:
            response = handler.handle(ServiceRequest.from_dict(payload))
            return response.to_dict()
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app

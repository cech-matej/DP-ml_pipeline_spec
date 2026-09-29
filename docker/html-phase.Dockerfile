FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src ./src
COPY configs ./configs

RUN pip install --no-cache-dir .[serving]

# The repository provides the HTTP wrapper as a reusable app factory.
# A deployment-specific bootstrap module should construct the configured PhaseRunner
# and expose it with `domain_detection.serving.http.create_app(phase)`.
CMD ["python", "-c", "print('Build complete: configure a PhaseRunner and launch create_app(phase) with uvicorn.')"]

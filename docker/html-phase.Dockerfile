FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src ./src
COPY configs ./configs

RUN pip install --no-cache-dir .

CMD ["python", "-m", "domain_detection.serving.http", "--phase", "configs/phases/html.yaml", "--host", "0.0.0.0", "--port", "8080"]

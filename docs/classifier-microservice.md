# Phase microservice contract

## One phase = one microservice

The deployment unit is a **phase**, containing:

- extractor(s);
- one or more classifiers;
- explanation logic;
- optional phase policy;
- a replaceable transport wrapper.

The phase core does not know whether its request arrived through HTTP or Kafka.

## Core API

The transport-independent core is:

```python
result = phase.run(phase_input)
```

The service handler wraps this with a stable wire-neutral contract:

```python
request = ServiceRequest.from_dict(payload)
response = handler.handle(request)
```

## Wire contract

Input:

```json
{
  "request_id": "req-123",
  "phase": "html",
  "phase_version": "3",
  "facts": {
    "html": {
      "body": "<html>...</html>"
    }
  }
}
```

Output:

```json
{
  "request_id": "req-123",
  "phase": "html",
  "phase_version": "3",
  "features": {
    "html-js-v5": {
      "script_count": 12,
      "external_script_ratio": 0.91,
      "form_count": 2
    }
  },
  "classifiers": [
    {
      "name": "html-js-classifier",
      "version": "9",
      "prediction": {
        "kind": "classification",
        "label": "phishing",
        "scores": {
          "benign": 0.01,
          "phishing": 0.96,
          "malware": 0.02,
          "spam": 0.01
        }
      },
      "explanation": {
        "method": "shap",
        "base_value": 0.13,
        "features": [
          {
            "name": "external_script_ratio",
            "value": 0.91,
            "contribution": 0.42
          },
          {
            "name": "form_count",
            "value": 2,
            "contribution": 0.18
          }
        ]
      }
    }
  ]
}
```

The concrete classifier payload is produced by the phase result serializer. The transport wrapper does not interpret classifier semantics.

## HTTP wrapper

`domain_detection.serving.http.create_app(phase)` creates a FastAPI application exposing:

```http
GET /health
POST /predict
```

Example configuration:

```yaml
transport:
  type: http
  http:
    host: 0.0.0.0
    port: 8080
```

HTTP is the default standalone transport because it is simple to invoke from local scripts, tests and a future deployment platform.

## Kafka wrapper

`domain_detection.serving.kafka.KafkaWrapper` consumes requests from one configured topic and publishes responses to another:

```yaml
transport:
  type: kafka
  kafka:
    bootstrap_servers: localhost:9092
    input_topic: thor.ml.html.request
    output_topic: thor.ml.html.response
    group_id: malicious-domain-html-v1
    client_id: malicious-domain-html
```

Parameters:

- `bootstrap_servers`: Kafka broker address(es);
- `input_topic`: topic from which this phase consumes requests;
- `output_topic`: topic to which this phase publishes responses;
- `group_id`: consumer group for this microservice instance set;
- `client_id`: optional Kafka client identifier.

The wrapper does not decide which phase to call next and does not access the THOR fact store. Topic routing/orchestration remains the caller's responsibility.

## Switching wrappers

The same phase instance can be exposed through either wrapper:

```text
                         +----------------+
HTTP ------------------->|                |
                         | ServiceHandler |----> PhaseRunner
Kafka input topic ------>|                |
                         +----------------+
                                |
                                +----> HTTP response
                                +----> Kafka output topic
```

There is no THOR adapter class in the architecture. Deployment chooses the wrapper.

## Explanation is part of inference

There is intentionally no separate `/explain` endpoint for normal inference. `/predict` returns predictions and local explanation data together.

A diagnostic endpoint may be added later, but it is not the production explanation contract.

## No collection metrics here

The phase service does not record:

- external API calls;
- API calls saved;
- collection cost;
- number of collectors executed.

Those belong to the collection/orchestration subsystem. It may record phase-local inference, extraction, classifier and explanation latency.

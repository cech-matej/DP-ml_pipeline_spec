# Phase microservice contract

## Important design choice

**One phase = one microservice**, containing:

- extractor(s);
- one or more classifiers;
- explanation logic.

This avoids repeatedly extracting the same input data for several classifiers.

## Core API

The transport-independent core is:

```python
result = phase.run(phase_input)
```

Transport adapters expose that same operation.

### Standalone HTTP

```http
GET /health
GET /metadata
POST /predict
```

`/predict` performs the complete phase operation, including local explanations.

There is intentionally no separate `/explain` endpoint for normal inference.

### Optional diagnostic endpoint

A separate endpoint such as `/explain-fixture` may be provided for debugging, but it is not part of the production inference contract.

## Input

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

The exact input shape is phase-specific. The important property is that collection has already happened.

## Output

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

## THOR adapter

The THOR adapter maps the same core result to a `service.result`.

THOR's service contract says services receive the complete snapshot of their declared `requires-facts` and return `provides-facts`; services do not access the fact store.

The adapter should therefore:

```text
service.dispatch
      |
      v
PhaseInput.from_thor_facts(...)
      |
      v
phase.run(...)
      |
      v
ThorServiceResult.from_phase_result(...)
```

The THOR result should expose classifier predictions and explanation facts under names declared by the service catalog.

## No collection metrics here

The phase service does not record:

- external API calls;
- API calls saved;
- collection cost;
- number of collectors executed.

Those belong to the collection/orchestration subsystem.

It may record phase-local metrics such as inference latency, extractor latency, classifier latency and explanation latency.

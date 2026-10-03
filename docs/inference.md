# Inference

## Batch-first contract

A phase accepts one service request containing one or more domains. A single-domain request is represented as a batch of one item.

```text
service request
      |
      +-- domain A
      +-- domain B
      +-- domain C
              |
              v
          same PhaseRunner
```

Each domain has a stable `domain_id` used to correlate its classifier results.

## Standalone

```text
local HTTP request
       |
       v
replaceable transport wrapper
       |
       v
     phase
       |
       +--> extractor(s)
       +--> classifier A
       +--> classifier B
       |
       v
  batched phase result
```

No collector or external service is required.

## Production/THOR

```text
THOR V1
   |
   | Kafka request
   v
Kafka wrapper
   |
   v
same ServiceHandler + PhaseRunner
   |
   | Kafka response
   v
THOR V1
```

The phase does not decide which future collector to invoke.

## One classify route, optional explanations

The same `/predict` route is used for both normal classification and classification with explanations. The request contains:

```json
{
  "request_id": "req-123",
  "phase": "html",
  "phase_version": "3",
  "include_explanations": false,
  "domains": [
    {
      "domain_id": "example.com",
      "facts": {}
    }
  ]
}
```

Set `include_explanations: true` to request local explanation data for that batch.

This deliberately supports two deployment strategies:

1. **Eager explanations:** request explanations for all classifications, retain the results, and let a later THOR V2 explainability system consume them.
2. **On-demand explanations:** normally classify with `include_explanations: false`; later re-submit selected domains with `include_explanations: true` when an explanation is needed.

The classifier implementation is the same in both cases. The only difference is whether the explanation step is executed for that request.

## Result shape

```json
{
  "request_id": "req-123",
  "phase": "html",
  "phase_version": "3",
  "result": {
    "domains": [
      {
        "domain_id": "example.com",
        "classifiers": [
          {
            "name": "html-js-classifier",
            "version": "9",
            "prediction": {
              "kind": "classification",
              "label": "phishing"
            },
            "explanation": {
              "method": "shap"
            }
          }
        ]
      }
    ]
  }
}
```

When explanations were not requested, the `explanation` field is omitted rather than containing a fabricated or empty explanation.

## Batch concurrency

Batching and horizontal scaling are separate controls:

- `domains[]` controls how many domains are carried by one request;
- `max_concurrent_domains` controls how many domains one phase instance processes concurrently;
- the deployment replica count controls how many copies of the phase exist;
- for Kafka, topic partition count limits useful consumer parallelism.

This permits shallow phases with high traffic to run many replicas while deeper phases can run fewer replicas because fewer domains reach them.

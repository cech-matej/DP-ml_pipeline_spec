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

Each domain has a `domain_id` used to correlate its classifier results. The phase does not require a separate request identifier.

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

## Request contract

The caller selects the phase by sending the request to the already deployed phase service. The request does **not** choose the phase version. Only one configured version of a phase is expected to be running in a deployment. The active version is reported in the response.

The request therefore contains only runtime input and the explanation mode:

```json
{
  "include_explanations": false,
  "domains": [
    {
      "domain_id": "example.com",
      "facts": {}
    }
  ]
}
```

`include_explanations` is optional and defaults to `false`. `domains` must contain at least one item. Each `domain_id` must be unique within the request so that results can be unambiguously matched to inputs.

There is intentionally no `request_id` field. For HTTP, the response naturally belongs to the HTTP request. For Kafka, the transport wrapper can preserve Kafka message keys/headers as transport metadata if the caller needs message-level correlation; this metadata is not part of the ML classification contract.

## One classify route, optional explanations

The same `/predict` route is used for both normal classification and classification with explanations. Set `include_explanations: true` to request local explanation data for that batch.

This deliberately supports two deployment strategies:

1. **Eager explanations:** request explanations for all classifications, retain the results, and let a later THOR V2 explainability system consume them.
2. **On-demand explanations:** normally classify with `include_explanations: false`; later re-submit selected domains with `include_explanations: true` when an explanation is needed.

The classifier implementation is the same in both cases. The only difference is whether the explanation step is executed for that request.

## Result shape

```json
{
  "phase": "html",
  "phase_version": "4",
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

`phase_version` is produced by the running service. The caller cannot select it in the request. When explanations were not requested, the `explanation` field is omitted rather than containing a fabricated or empty explanation.

## Batch concurrency

Batch size and concurrency are separate:

- `domains[]` controls how many domains are carried by one request;
- `execution.max_concurrent_domains` controls how many domains one phase instance processes concurrently;
- domains beyond that limit wait in bounded in-process work until an execution slot is free;
- the deployment replica count controls how many copies of the phase exist;
- for Kafka, topic partition count limits useful consumer parallelism.

For example, with `max_concurrent_domains: 4` and a request containing 10 domains, one instance processes at most 4 domains concurrently. The other 6 wait and are processed as earlier domains finish. The request is not split into separate transport requests by the phase.

This permits shallow phases with high traffic to run many replicas while deeper phases can run fewer replicas because fewer domains reach them.

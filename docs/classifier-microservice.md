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

## Batch wire contract

Input:

```json
{
  "include_explanations": false,
  "domains": [
    {
      "domain_id": "example.com",
      "facts": {
        "html-js": {"body": "<html>...</html>"},
        "dom-fingerprint": {"node_count": 42}
      }
    },
    {
      "domain_id": "example.org",
      "facts": {}
    }
  ]
}
```

Output:

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
      },
      {
        "domain_id": "example.org",
        "classifiers": []
      }
    ]
  }
}
```

`domains` is always a list. One domain is simply a list containing one domain. `domain_id` values must be unique within a request.

The request does not contain `request_id` or `phase_version`. The active phase version is deployment configuration and is returned by the service. For HTTP, the response is naturally associated with the request. For Kafka, message keys/headers can carry transport-level correlation metadata without putting it into the ML contract.

`include_explanations` is a request-level flag. It controls whether the same `/predict` operation also executes the configured explanation logic.

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

HTTP is the default standalone transport because it is simple to invoke from local scripts, tests and a deployment platform.

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
- `group_id`: consumer group shared by replicas of this phase;
- `client_id`: optional Kafka client identifier.

The wrapper does not decide which phase to call next and does not access the THOR fact store. Topic routing/orchestration remains the caller's responsibility.

## Switching wrappers

The same phase implementation can be exposed through either wrapper:

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

There is no THOR adapter class. Deployment chooses the wrapper.

## Horizontal scaling

Multiple instances of the same phase are expected:

```text
Kafka input topic
      |
      +----> phase instance 1
      +----> phase instance 2
      +----> phase instance 3
      |
      v
Kafka output topic
```

All Kafka replicas of the same phase use the same `group_id`; Kafka distributes partitions across active consumers. The topic therefore needs enough partitions to support the desired consumer parallelism.

For HTTP, multiple replicas can sit behind a load balancer. See `docs/http-load-balancing.md` for a concrete Docker Compose + HAProxy example and the exact commands for running 1, 2 or more phase instances.

Replica count is a deployment concern, not a classifier or extractor concern. Different phases may intentionally use different replica counts, so deeper pipeline phases can consume fewer resources when their input volume is smaller.

## Bounded batch concurrency

A phase may receive many domains in one request. The phase configuration can bound the number processed concurrently by one instance:

```yaml
execution:
  parallel_classifiers: true
  max_concurrent_domains: 4
```

If a request contains more than 4 domains, the additional domains wait in the same request until one of the four execution slots becomes available. They are not rejected solely because the batch is larger than the limit.

This is independent of horizontal replica count. Replica count is configured by the deployment/orchestrator, not in the phase manifest. See `configs/deployments/` and `docs/scaling.md`.

## Explanation mode

There is intentionally no separate production `/explain` endpoint. `/predict` is the single classify route.

- `include_explanations: false` -> prediction only;
- `include_explanations: true` -> prediction plus local explanation.

This makes it possible to benchmark eager explanation storage against later on-demand reclassification without creating a second classifier API.

## No collection metrics here

The phase service does not record:

- external API calls;
- API calls saved;
- collection cost;
- number of collectors executed.

Those belong to the collection/orchestration subsystem. It may record phase-local inference, extraction, classifier and explanation latency.

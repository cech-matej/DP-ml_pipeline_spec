# Phase specification

A **phase is one microservice**.

It contains:

- an extractor definition and implementation for the information boundary;
- one or more feature-vector schemas;
- one or more classifiers;
- explanation implementations;
- optional phase-level policy;
- a replaceable transport wrapper (HTTP or Kafka).

## Phase YAML reference

### `phase.name`

Stable logical name of the phase, such as `html`. It identifies the microservice capability.

### `phase.version`

Version of the phase composition and behavior. Increment it when extractor membership/behavior, feature schemas, classifier membership/configuration, explanation behavior, policy or execution semantics change.

### `phase.information_boundary`

The information boundary represented by the phase input. For `html`, the phase expects the HTML-level facts/representation to already have been collected. The phase does not collect them itself.

### `extractors[].name`

Logical name of an extractor included in the phase. It identifies which feature-producing implementation is used.

### `extractors[].schema`

Feature schema produced by that extractor. This connects the extractor to the authoritative versioned feature contract.

### `classifiers[].name`

Classifier logical name included in the phase.

### `classifiers[].version`

Classifier version the phase has pinned. This prevents a phase from silently changing model versions.

### `classifiers[].input_schema`

Feature schema consumed by the classifier. It should match one of the schemas produced by the phase's extractors.

### `execution.parallel_classifiers`

Whether independent classifiers may execute concurrently after their required features are available. `true` is the intended configuration when there are no dependencies between classifiers.

### `execution.max_concurrent_domains`

Maximum number of domains that one phase instance may process concurrently. This is a **per-instance concurrency limit**, not the total capacity of the phase deployment. If a request contains more domains than this value, the domains are processed in bounded waves: at most `max_concurrent_domains` domains run at once, while the remaining domains wait in the request until capacity becomes available. The request is not rejected merely because its batch is larger than this value.

This setting is independent of the number of phase instances. For example, `max_concurrent_domains: 4` with 5 replicas gives up to 20 domains being processed concurrently across the deployment, subject to available resources and the transport/deployment layer.

### `execution` and horizontal replicas

`execution.max_concurrent_domains` controls concurrency **inside one running instance**. The number of running instances is a deployment concern and is not part of the phase manifest because it may differ between environments. Configure it in a deployment manifest or orchestration configuration. See `docs/scaling.md` and `docs/http-load-balancing.md`.

For the example Docker Compose deployment, the desired replica count is represented by the `replicas` value in `config/deployments/example-html-http.yaml`, while `docker compose up --scale html-phase=N` is the concrete local command that creates N instances. In a Kubernetes deployment, the equivalent setting would be the Deployment `spec.replicas`.

### `policy.type`

Mechanism used to convert heterogeneous classifier results into an optional phase-level outcome. The current example uses `rule_based`.

### `policy.outputs`

Allowed phase-level output labels. These are the outputs of the phase policy, not necessarily the complete set of classifier labels.

### `policy.otherwise`

Fallback phase-level outcome when no policy rule produces a more specific result.

## Current phase manifest

`config/phases/example_html.yaml` defines the HTML phase, version `4`, with the `html` information boundary. It runs the HTML/JS and DOM/fingerprint extractors and pins the corresponding classifier versions. Independent classifiers are configured to run in parallel.

Example:

```yaml
phase:
  name: html
  version: 4
  information_boundary: html

extractors:
  - name: html-js
    schema: html-js-v5
  - name: dom-fingerprint
    schema: dom-fingerprint-v2

classifiers:
  - name: html-js-classifier
    version: 9
    input_schema: html-js-v5
  - name: dom-phishing-classifier
    version: 5
    input_schema: dom-fingerprint-v2

execution:
  parallel_classifiers: true

policy:
  type: rule_based
  outputs:
    - benign
    - phishing
    - malware
    - spam
    - uncertain
  otherwise: uncertain
```

## Why the extractor belongs to the phase

A phase owns the transformation from the received information boundary to model-ready features. This ensures training and inference use the same implementation.

## Multiple classifiers

Classifiers can be heterogeneous:

- binary malicious/benign model;
- multiclass phishing/malware/spam/benign model;
- DGA detector;
- similarity/fingerprint detector;
- calibrated score model.

The phase does not require all classifiers to share the same output space.

## Execution

Where feature dependencies permit, classifiers run concurrently after feature extraction.

```python
features = extractor.extract(input_data)

results = await run_in_parallel(
    html_js_classifier,
    dom_phishing_classifier,
    features,
)
```

The phase result contains all classifier results and explanations. A separate phase policy may derive a phase-level decision from them.

## Versioning

A phase version changes when any of these change:

- extractor membership or behavior;
- feature schema membership/version;
- classifier membership/version;
- classifier configuration;
- explanation implementation;
- phase policy;
- execution semantics.


## Transport configuration

The phase manifest may select its deployment wrapper:

### `transport.type`

Selects the wire wrapper. Supported examples are `http` for standalone deployment and `kafka` for a Kafka-based deployment such as the future THOR V1 integration.

### `transport.http`

HTTP listener settings. `host` is the bind address and `port` is the listener port. These values affect only the HTTP wrapper.

### `transport.kafka`

Kafka wrapper settings:

- `bootstrap_servers`: Kafka broker address(es);
- `input_topic`: topic consumed by this phase microservice;
- `output_topic`: topic receiving the phase response;
- `group_id`: consumer group used by the service;
- `client_id`: optional Kafka client identifier.

Changing `transport.type` and its transport-specific configuration should not require changes to feature extractors, classifiers, policies or the phase runner.

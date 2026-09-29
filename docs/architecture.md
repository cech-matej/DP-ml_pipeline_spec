# Architecture

## 1. Standalone-first principle

The ML pipeline must not depend on THOR being implemented.

The ML subsystem owns:

1. feature extraction from already-available input data/facts;
2. feature-vector validation;
3. classifier execution;
4. per-inference explanations;
5. model loading;
6. model training/evaluation/tuning;
7. phase-level decision policy, if a phase has one.

It does **not** own:

- DNS/WHOIS/TLS/HTML collection;
- external API calls;
- crawling;
- rate-limit management;
- Kafka orchestration/business routing;
- THOR fact-store access;
- decisions about which information should be collected next.

This makes training and testing possible without starting the collection/orchestration system.

## 2. Phase boundary

The primary deployment unit is a **phase microservice**:

```text
phase
 ├── transport wrapper (HTTP or Kafka)
 ├── service handler
 ├── feature extractor(s)
 ├── feature-vector validator
 ├── classifier A
 ├── classifier B
 ├── ...
 ├── explanation adapters
 └── phase result builder
```

A phase receives data for one information boundary. For example, an HTML phase may receive HTML/DOM facts already collected by another component.

The extractor runs once per required feature view, then classifiers that depend on that view can run in parallel.

## 3. Source-code separation

At source level, keep reusable layers separate:

```text
wire message
     |
     v
transport wrapper
     |
     v
ServiceRequest
     |
     v
PhaseRunner
     |
     +----> feature extractor(s)
     |          |
     |          v
     |      validated feature vector
     |          |
     |          +----> classifier A
     |          +----> classifier B
     |          +----> classifier C
     |
     v
PhaseResult
     |
     v
ServiceResponse
     |
     +----> HTTP response
     +----> Kafka output message
```

The extractor contains feature computation logic. The classifier contains model logic. Neither contains collection or transport logic.

The same Python extractor object/function is imported by both training and inference.

## 4. Interchangeable transport wrappers

The important boundary is the **transport wrapper**.

Both wrappers call the same service handler:

```python
request = ServiceRequest.from_dict(wire_payload)
response = handler.handle(request)
wire_payload = response.to_dict()
```

The HTTP wrapper exposes the handler through HTTP. The Kafka wrapper consumes an input topic, calls the same handler, and publishes the response to the configured output topic.

```text
Standalone deployment
HTTP ---> ServiceHandler ---> PhaseRunner ---> HTTP

THOR V1 deployment
Kafka input topic ---> ServiceHandler ---> PhaseRunner ---> Kafka output topic
```

Switching transport should require only configuration/deployment changes:

```yaml
transport:
  type: http
```

or:

```yaml
transport:
  type: kafka
  kafka:
    bootstrap_servers: localhost:9092
    input_topic: thor.ml.html.request
    output_topic: thor.ml.html.response
    group_id: malicious-domain-html-v1
```

The phase code does not import Kafka, HTTP, THOR or the fact store. Kafka topic names are properties of the deployment wrapper for that microservice.

The current Kafka example deliberately keeps the message contract generic. When THOR V1 defines its final Kafka envelope, that envelope belongs at the transport serialization boundary rather than requiring changes to extractors or classifiers.

## 5. THOR integration

THOR V1 documents a service boundary in which the engine sends a complete snapshot of declared `requires-facts`, and the service returns facts for the engine to write. The ML service can satisfy that boundary through its Kafka wrapper without adding THOR-specific logic to the phase core.

THOR V1's documented service result model also supports returning service-produced facts/results.

The responsibility split is:

- **THOR**: orchestration, collection, gates, routing and fact-store integration;
- **Kafka wrapper**: ingest topic, output topic, serialization and message delivery;
- **ML phase**: extraction, validation, classifiers, explanations and optional phase policy.

THOR V1's ordered steps and gates remain outside the phase.

## 6. Separation from collection

The classification service must never make a decision such as "collect HTML now". It can return:

- classifier labels/scores;
- explanations;
- confidence/uncertainty;
- optional phase-level decision.

The future THOR flow/gates decide whether another information boundary is requested. THOR V1 explicitly models ordered steps and gates, with the pipeline becoming more expensive as it progresses.

## 7. Lineage

```text
raw source files
  |
  v
immutable W&B dataset artifact
  |
  v
feature extraction
  |
  v
versioned feature dataset artifact
  |
  v
training run
  |
  v
model artifact/version
  |
  v
classifier version
  |
  v
phase version
  |
  v
future THOR flow version
```

The dataset artifact is versioned before feature extraction. Feature artifacts record the exact input dataset artifact/version, feature schema version and feature-code commit.

## 8. Operational independence

The phase can be run with standalone HTTP and no THOR process. Kafka is an optional deployment transport.

No collector or THOR process is required for local training/testing.

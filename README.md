# Malicious Domain Detection ML Pipeline

A standalone, reusable ML pipeline for malicious-domain detection that can later be integrated into THOR V1 without changing the feature extraction or classifier implementations.

## Core design

```text
INPUT FACTS / LOCAL FIXTURE
             |
             v
+----------------------------+
|   Phase ML microservice    |
|                            |
|   reusable extractor(s)    |
|            |               |
|            v               |
|     Feature vector         |
|       //       \\          |
|       v         v          |
| classifier A  classifier B |
|       \\       //          |
|        v       v           |
|  inference + explanations  |
+----------------------------+
             |
             v
 typed classifier results
```

A **phase is one microservice**. A phase contains the extractor definition/implementation for that information boundary and one or more classifiers. The classifiers run against the feature vectors produced by that phase.

The phase does **not collect data**. Collection belongs to another module/system. The same phase can therefore be run:

- standalone from local files or fixtures;
- in training/evaluation jobs;
- as an HTTP service;
- later as a THOR Kafka service.

## Important decisions

- Dataset versioning happens before feature extraction.
- W&B is the primary experiment, artifact, dataset and model-management system.
- MLflow remains a documented fallback, not the primary stack.
- Feature schemas are executable contracts: feature names and types are defined once in the versioned feature-vector schema.
- Extractors return raw feature values and are validated against that schema; they do not duplicate feature type declarations.
- The exact same extractor code is used for training and inference.
- One phase may contain heterogeneous classifiers.
- Classifiers support binary, multiclass, multilabel and non-classification scoring/detection outputs.
- Every classify request uses the same route/contract; `include_explanations` controls whether local explanations are returned.
- The classification pipeline does not own collection, external API calls, rate limits or collection-cost metrics.
- Model training/evaluation is model-centric. Stage/cascade metrics are collected only when evaluating an assembled phase/stage/cascade, not during ordinary model training.
- Outlier handling is model-specific and never mutates the canonical dataset.
- A phase accepts batches of domains and can run multiple domains concurrently with a configurable bound. Multiple identical phase instances can run for load balancing, with replica counts chosen independently per pipeline phase.
- Transport is a replaceable wrapper around the same phase implementation. Standalone uses HTTP; THOR V1 can use the Kafka wrapper with per-microservice input/output topics. No THOR-specific adapter is required in the phase core.

## Repository structure

```text
src/domain_detection/
  features/        reusable feature extractors + schema validation
  classifiers/     reusable model implementations and wrappers
  phases/          phase composition and execution
  policies/        optional phase-level decision policies
  serving/         interchangeable HTTP/Kafka transport wrappers
  training/        dataset loading, training and tuning
  explainability/  local/global explanation adapters
tests/
configs/
docs/
```

## Interchangeable service wrappers

The phase core is independent of the wire protocol:

```text
                 +------------------+
HTTP request --->|                  |---> HTTP response
                 |  ServiceHandler  |
Kafka message -->|   PhaseRunner    |---> Kafka message
                 +------------------+
```

Both wrappers use the same `ServiceRequest` / `ServiceResponse` contract. The request is batch-first (`domains[]`) and has one `include_explanations` flag. To run standalone, select `type: http`. To deploy behind THOR V1, select `type: kafka` and set the microservice's `input_topic` and `output_topic`. Extractors, classifiers, policies and explainability code do not change. The Kafka wrapper is a transport wrapper, not a THOR business-logic adapter. Multiple Kafka instances of the same phase share a consumer group for load balancing; deeper phases can be deployed with fewer replicas. For HTTP, see `docs/http-load-balancing.md` for a concrete HAProxy + Docker Compose setup.

Read `docs/DOCUMENT_INDEX.md` first.

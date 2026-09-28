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
- Kafka orchestration;
- THOR fact-store access;
- decisions about which information should be collected next.

This makes training and testing possible without starting the future collection/orchestration system.

## 2. Phase boundary

The primary deployment unit is a **phase microservice**:

```text
phase
 ├── input adapter
 ├── feature extractor(s)
 ├── feature-vector validator
 ├── classifier A
 ├── classifier B
 ├── ...
 ├── explanation adapters
 └── phase result builder
```

A phase receives data for one information boundary. For example, an HTML phase may receive the HTML/DOM facts already collected by another component.

The extractor runs once per required feature view, then classifiers that depend on that view can run in parallel.

## 3. Source-code separation

At source level, keep two reusable layers separate:

```text
feature extraction
       |
       v
validated feature vector
       |
       +----> classifier A
       +----> classifier B
       +----> classifier C
```

The extractor contains feature computation logic. The classifier contains model logic. Neither contains collection logic.

The same Python extractor object/function is imported by both training and inference.

## 4. THOR integration

THOR V1 already defines a service boundary in which the engine sends a complete snapshot of declared `requires-facts`, and the service returns facts for the engine to write. The ML service should therefore be implemented behind an adapter rather than coupled to THOR internals.

```text
                    standalone
                       |
local fixture ----> Phase Core <---- THOR adapter
                       |
                    result
```

The Phase Core has no Kafka or Redis dependency.

The future THOR adapter maps:

```text
THOR service.dispatch.data.facts
            |
            v
      PhaseInput
            |
            v
      extractor(s)
            |
            v
       classifiers
            |
            v
      PhaseResult
            |
            v
THOR service.result.data.facts
```

This matches THOR V1's documented `service.result` model, where service-produced values are returned as facts.

## 5. Separation from collection

The classification service must never make a decision such as "collect HTML now". It can return:

- classifier labels/scores;
- explanations;
- confidence/uncertainty;
- optional phase-level decision.

The future THOR flow/gates decide whether another information boundary is requested. THOR V1 explicitly models ordered steps and gates, with the pipeline becoming more expensive as it progresses.

## 6. Lineage

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

## 7. Operational independence

The phase must be runnable with:

```text
python -m domain_detection.phase_runner   --phase configs/phases/html.yaml   --input tests/fixtures/html_case.json
```

No Kafka, Redis, collector or THOR process is required for this mode.

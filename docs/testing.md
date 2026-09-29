# Testing

## 1. Unit tests

Test:

- individual feature functions;
- extractor edge cases;
- classifier wrappers;
- output mappings;
- explanation adapters.

## 2. Feature schema contract tests

For every extractor:

- all declared features are produced;
- no undeclared features are produced;
- runtime types match schema types;
- nullability rules are respected;
- categorical values match vocabularies;
- deterministic ordering/serialization is preserved;
- feature availability boundary is respected.

A schema mismatch must raise an explicit error.

## 3. Reuse tests

The same fixture must pass through the same extractor in:

- feature-generation tests;
- model training tests;
- standalone inference tests.

This protects against accidentally creating separate training/inference feature logic.

## 4. Classifier contract tests

Test:

- model loading;
- schema compatibility;
- output shape;
- class mapping;
- multiclass probabilities;
- specialized detector scores;
- explanation presence;
- per-feature contribution alignment;
- model/version metadata.

## 5. Phase microservice contract tests

Run the same fixture through:

```text
Phase Core
Standalone HTTP wrapper
Kafka wrapper
```

and compare the semantic result.

## 6. Integration tests

When THOR exists, verify:

- dispatch facts map correctly to phase input;
- returned classifier facts are correctly declared;
- explanation facts are retained;
- phase failure maps to service error/skip semantics;
- no service attempts to access the fact store.

## 7. Cascade tests

Only the assembled cascade tests measure:

- early exit;
- average phase reached;
- collection decisions;
- downstream calls avoided.

Those are not model-training metrics.

## 8. Regression fixtures

Keep a stable, versioned regression set separate from training data. It should cover:

- benign;
- phishing;
- malware;
- DGA;
- ambiguous/mixed cases;
- malformed input;
- missing optional facts;
- explanation edge cases.

## 9. Transport contract tests

The transport layer should be tested independently from the model. In particular, verify that:

- an HTTP JSON payload and a Kafka JSON payload deserialize to the same `ServiceRequest`;
- both wrappers invoke the same `ServiceHandler`;
- a `PhaseResult` serializes to the same semantic `ServiceResponse` regardless of transport;
- changing `input_topic`/`output_topic` does not change phase behavior.

The repository includes `tests/test_transport_contracts.py` as a minimal example.

# Implementation plan

The documentation describes the target architecture. The implementation can be built incrementally.

## Part 1

1. Feature schema loader + validator.
2. Reusable extractor interface.
3. Classifier interface.
4. Phase runner.
5. Standalone JSON fixture input/output.
6. SHAP/local explanation contract.
7. W&B dataset/model artifact helpers.
8. Training CLI.
9. Model-specific outlier filtering.
10. HTTP adapter.
11. Contract tests.

## Part 2: THOR integration

1. THOR dispatch adapter.
2. THOR result adapter.
3. Service catalog entries.
4. Kafka transport.
5. Integration tests against THOR schemas.

No feature extractor or classifier should need to change merely because the transport changes from standalone to THOR.

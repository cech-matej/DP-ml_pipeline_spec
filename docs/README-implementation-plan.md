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
10. HTTP transport wrapper.
11. Kafka transport wrapper.
12. Contract tests.

## Part 2: THOR integration

1. Finalize the Kafka wire envelope against the THOR V1 service schema.
2. Service catalog entries.
3. Integration tests against THOR schemas/topics.

No feature extractor, classifier, policy or phase runner should need to change merely because the transport changes from standalone HTTP to THOR Kafka.

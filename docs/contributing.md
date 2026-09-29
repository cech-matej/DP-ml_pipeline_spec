# Contributing

## Adding a feature extractor

1. Create/update the versioned feature schema.
2. Implement reusable extraction logic.
3. Add schema validation tests.
4. Add fixtures.
5. Verify the extractor works for both feature generation and inference.
6. Version the feature schema if semantics changed.

Do not duplicate the feature schema in Python or classifier configuration.

## Adding a classifier

1. Implement the classifier wrapper.
2. Declare its input feature schema.
3. Declare its output type/classes.
4. Declare its explanation method.
5. Add model-specific outlier policy if needed.
6. Add unit/contract tests.
7. Train/evaluate independently.
8. Register/publish the model artifact.
9. Add it to a phase only after model-level validation.

## Adding a phase

1. Define its information boundary.
2. Define input facts/fixture shape.
3. Add extractor(s).
4. Add classifier(s).
5. Add phase policy if required.
6. Add standalone tests.
7. Add service contract tests.
8. Add or configure a transport wrapper; do not add THOR-specific logic to the phase core.

## Version rules

- dataset changes -> new dataset artifact version;
- feature semantics/types -> new feature schema version;
- extractor behavior -> new extractor/code version;
- model behavior -> new model version;
- classifier configuration/output contract -> new classifier version;
- phase membership/policy -> new phase version;
- THOR flow changes -> new flow version.

## Pull requests

A model PR should include:

- dataset artifact/version;
- feature schema;
- extractor commit;
- classifier/model version;
- metrics;
- explanation method;
- outlier policy;
- tests;
- known limitations.

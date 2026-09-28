# W&B metadata convention

W&B is the primary tracking/versioning system.

## Run tags

Required:

```text
project
phase.name
classifier.name
classifier.version
feature.schema
dataset.artifact
outlier.policy
git.commit
```

Recommended:

```text
framework
framework.version
python.version
random.seed
training.machine
```

## Artifacts

Suggested artifact types:

```text
dataset
feature-dataset
model
explainability-report
regression-fixture
```

Suggested names:

```text
domain-dataset
feature-html-js
model-html-js-classifier
model-dom-phishing
```

Use immutable artifact versions/digests for reproducible runs.

## Model metadata

Every model artifact should contain:

- classifier manifest;
- feature schema;
- class mapping;
- training config;
- outlier policy;
- metrics;
- explanation configuration;
- source Git commit;
- Python/dependency environment.

W&B supports artifact lineage by recording artifacts as run inputs, and artifacts can be downloaded and verified against their manifests.

## Cascade/phase evaluation

If a separate evaluation assembles several classifiers into a phase/cascade, record that as its own W&B run. Keep its metrics separate from individual model training runs.

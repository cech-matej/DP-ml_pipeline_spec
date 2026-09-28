# Dataset versioning

## Dataset first

The canonical dataset is versioned **before feature extraction**.

```text
CSV / Parquet / other source files
        |
        v
validated canonical dataset artifact
        |
        v
immutable W&B artifact version
        |
        v
feature extraction
        |
        v
feature dataset artifact
```

W&B Artifacts are the primary mechanism for storing/versioning dataset and feature-data artifacts. W&B records artifact use as a run dependency, which gives the training run explicit input lineage.

## Required dataset metadata

```yaml
dataset:
  name: domains-labeled
  version: <W&B artifact version/digest>

schema:
  version: 3

source:
  files:
    - path: source.parquet
      sha256: <hash>

labeling:
  definition: documented-label-definition

split:
  strategy: time
  seed: null
```

Never train from `latest`. Training jobs receive an immutable artifact reference.

## Feature dataset lineage

Every feature dataset must record:

- source dataset artifact/version;
- feature schema version;
- feature extractor Git commit;
- extraction configuration hash;
- generation timestamp;
- code/environment version.

## Dataset validation

Before publishing a dataset version, check:

- schema;
- duplicate identifiers;
- missing labels;
- invalid labels;
- label distribution;
- temporal leakage;
- campaign/source leakage;
- train/test contamination;
- feature availability at inference time.

The canonical dataset is never modified because one classifier needs a different preprocessing or outlier policy. Model-specific filtering happens later in the training job.

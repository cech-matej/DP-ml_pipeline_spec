# Outlier treatment

Outlier handling is **model-specific**.

An observation that is an outlier for one model must not be deleted from the canonical dataset or from another model's training set.

## Outlier YAML reference

### `outlier_policy.name`

Stable versioned name of the outlier policy. This is recorded in training lineage so a model can be reproduced with the same filtering policy.

### `outlier_policy.scope`

Defines where the policy may be applied. The current contract uses `training_only`: filtering is permitted only on the training partition.

### `method.type`

Outlier detection algorithm, such as `isolation_forest`. Other methods may include robust z-score, IQR or domain-specific rules.

### `method.contamination`

For Isolation Forest, the expected proportion of observations treated as outliers by the detector. It is a model-training configuration parameter, not a statement about the true prevalence of malicious domains.

### `action.remove`

Whether observations identified by the policy are removed from the training data. If `false`, the detector may still be used for diagnostics or metadata without deleting rows.

### `minimum_training_rows`

Safety floor for the filtered training partition. Training must fail rather than continue if applying the policy would leave fewer rows than this value.

## Current policy

`config/outliers/example_html-js.yaml` uses Isolation Forest with `0.01` contamination, removes detected training outliers, and requires at least `10,000` rows after filtering.

## Pipeline

```text
canonical dataset
      |
      +--------------------+
      |                    |
      v                    v
model A training       model B training
      |                    |
outlier policy A       outlier policy B
      |                    |
      v                    v
fit model A            fit model B
```

## Rules

- Apply only to the training partition by default.
- Never mutate the source dataset artifact.
- Never silently apply the same policy to validation/test.
- Record the policy version in W&B.
- Record how many rows were removed.
- Record identifiers/hashes of removed rows in a private audit artifact where appropriate.
- Refuse to train if filtering would leave fewer than the configured minimum.
- Outlier detection must itself be fitted only on training data.

Validation and test sets remain representative of the intended evaluation population unless a documented evaluation protocol says otherwise.

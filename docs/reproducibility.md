# Reproducibility

Required lineage:

```text
model artifact
  |
training run
  |
feature dataset artifact
  |
feature schema version
  |
extractor Git commit
  |
source dataset artifact/version
```

Every W&B training run records:

```text
dataset.artifact
dataset.version/digest
feature.schema
feature.dataset.artifact
feature.code.commit
classifier.code.commit
training.config
outlier.policy
random.seed
python.version
dependency.lock.hash
```

## Reproduction

1. Resolve the exact model artifact.
2. Resolve its training run.
3. Resolve the exact dataset artifact/version.
4. Checkout the recorded Git commit.
5. Recreate the environment.
6. Run the same extractor.
7. Apply the same model-specific outlier policy.
8. Re-run training/evaluation.
9. Compare metrics, predictions and explanations.

Never resolve an input using `latest` during a reproduction.

## Inference provenance

Each inference result should contain:

- phase version;
- classifier version;
- model artifact/version;
- feature schema version;
- extractor code version;
- explanation method/version.

This allows the downstream explainability system to identify exactly what produced each contribution.

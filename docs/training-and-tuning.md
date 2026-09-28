# Training and tuning

## Model-centric workflow

```text
immutable dataset artifact
        |
        v
feature extraction using production extractor
        |
        v
feature dataset artifact
        |
        v
train / validation / test
        |
        v
model-specific outlier filtering on TRAIN only
        |
        v
training run
        |
        v
tuning
        |
        v
candidate model
        |
        v
test evaluation + explainability
        |
        v
W&B model artifact / registry
```

Training a model does not require a complete phase or cascade.

## No stage metrics during model training

Do not report:

- average stage reached;
- early-exit rate;
- collection calls;
- collection cost.

Those are orchestration/cascade metrics and only make sense when an assembled system is evaluated.

A model training run should instead report:

- class-wise precision/recall;
- macro/micro metrics as appropriate;
- FPR/FNR where meaningful;
- PR-AUC/ROC-AUC where meaningful;
- calibration;
- confusion matrix;
- inference latency;
- explanation latency;
- explanation availability;
- model size.

## Reusing feature extraction

Training must invoke the same extractor used by inference:

```python
features = extractor.extract(input_data)
```

Never maintain a second training-only implementation.

## W&B

W&B is the primary system for experiments, artifacts, datasets and models. Its Artifacts API can be used to record dataset/model inputs and retrieve exact artifact versions.

The academic offering currently advertises a free academic license with 200 GB cloud storage.

## Tuning

Optuna may be used locally or as the search engine behind W&B-tracked runs.

Every trial records:

- immutable dataset version;
- feature schema;
- extractor code commit;
- classifier code commit;
- model configuration;
- random seed;
- metrics;
- outlier policy;
- explanation configuration.

Threshold tuning uses validation data. The final test set remains untouched until the candidate is frozen.

## Model acceptance

A model is accepted only when:

- feature schema is compatible;
- model artifact is reproducible;
- class mapping/output contract is explicit;
- local explanation contract is satisfied;
- outlier policy is recorded;
- regression tests pass;
- test-set evaluation is complete.

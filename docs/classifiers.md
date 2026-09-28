# Classifier specification

A classifier is a reusable model component. It is not responsible for data collection.

## Supported output families

The classifier contract must support:

1. **binary classification**
   - classes such as `benign`, `malicious`;

2. **multiclass classification**
   - e.g. `benign`, `phishing`, `malware`, `spam`;

3. **multilabel classification**
   - multiple threat labels can be active;

4. **specialized detection/scoring**
   - DGA score;
   - phishing-template similarity;
   - nearest-neighbour score;
   - fingerprint match;
   - other domain-specific detectors.

Therefore there is no universal `positive_class` field.

## Classifier YAML reference

The classifier manifest describes identity, implementation, feature input, output semantics, explainability and optional training configuration.

### `classifier.name`

Stable logical name of the classifier. It is the identifier used by the phase and model registry.

### `classifier.version`

Version of the classifier definition/model contract. Increment when the classifier's model-visible behavior or configuration changes in a way that requires a distinct registered version.

### `implementation.framework`

Model or detector framework/implementation family, such as `lightgbm` or `similarity-detector`. It tells the runtime how the classifier is implemented and can be used to select the correct loader/explanation adapter.

### `implementation.source_module`

Python module containing the classifier implementation/adapter. The source code is versioned in Git; this field tells the runtime where the implementation is located.

### `input.feature_schema`

Exact feature schema required by the classifier. It must match the schema produced by the phase extractor. This is a reference, not a second declaration of feature names/types.

### `output.type`

Declares the prediction family. Supported examples are `binary`, `multiclass`, `multilabel` and `score`. The consumer must interpret the remaining output fields according to this type.

### `output.classes`

The ordered class vocabulary for classification outputs. It is required for multiclass/multilabel models and is not needed for a scalar `score` detector.

### `output.score_semantics`

Meaning of the numeric class scores, for example `calibrated_probability`. This prevents consumers from assuming that every score is a probability.

### `output.score_name`

Name of a scalar score for `output.type: score`, such as `phishing_similarity` or `dga_probability`.

### `output.range`

Expected numeric range for a scalar score. `[0.0, 1.0]` means the score contract is bounded to that interval; it does not by itself mean the score is a calibrated probability.

### `explainability.local.method`

Method used to produce per-inference feature/component contributions, such as `shap` or `similarity_components`.

### `explainability.local.required`

Whether a production model registration is valid only if the declared local explanation can be produced. `true` means the runtime must reject a model that cannot satisfy the explanation contract.

### `explainability.global.methods`

Global explanation methods recorded for the model, such as native model gain or mean absolute SHAP values. These describe overall model behavior and are distinct from the local explanation returned for an individual inference.

### `training.outlier_policy`

Reference to a versioned model-specific outlier policy. The policy is applied to the training partition only and does not modify the canonical dataset.

## Classifier manifest

```yaml
classifier:
  name: html-js-classifier
  version: 9

implementation:
  framework: lightgbm
  source_module: domain_detection.classifiers.html_js

input:
  feature_schema: html-js-v5

output:
  type: multiclass
  classes: [benign, phishing, malware, spam]
  score_semantics: calibrated_probability

explainability:
  local:
    method: shap
    required: true
  global:
    methods: [native_gain, shap_mean_abs]

training:
  outlier_policy: html-js-outliers-v1
```

## Current classifier manifests

### `configs/classifiers/html-js.yaml`

A LightGBM multiclass classifier using `html-js-v5`, with four classes, calibrated-probability score semantics, required SHAP local explanations, native gain/mean-absolute-SHAP global explanations, and the `html-js-outliers-v1` training policy.

### `configs/classifiers/dom-phishing.yaml`

A similarity detector using `dom-fingerprint-v2`. Its output is the scalar `phishing_similarity` in `[0, 1]`. Local explanations use similarity components and global explanation uses component importance. It does not declare an outlier policy because the current manifest does not require one.

## Python contract

```python
class Classifier:
    def fit(self, X, y, config): ...
    def predict(self, X): ...
    def explain(self, X): ...
    def metadata(self): ...
```

`predict()` returns a typed `ClassifierPrediction`, not a fixed malicious/benign object.

For multiclass models it can contain:

```json
{
  "kind": "classification",
  "label": "phishing",
  "scores": {
    "benign": 0.01,
    "phishing": 0.96,
    "malware": 0.02,
    "spam": 0.01
  }
}
```

For a DGA detector:

```json
{
  "kind": "score",
  "score_name": "dga_probability",
  "score": 0.94
}
```

## Separation of concerns

Classifier:

> What does this model say about the evidence?

Phase policy:

> Given the outputs of the classifiers in this phase, what phase-level decision should be emitted?

THOR/orchestration:

> Should the system collect another information boundary?

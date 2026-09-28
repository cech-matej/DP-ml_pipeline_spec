# Inference

## Standalone

```text
input fixture / local facts
       |
       v
     phase
       |
       +--> extractor
       |
       +--> classifier A
       +--> classifier B
       |
       +--> per-feature explanations
       |
       v
  phase result
```

No collector or external service is required.

## Production/THOR

```text
THOR
  |
  | service.dispatch with facts
  v
phase microservice
  |
  | service.result with predictions + explanations
  v
THOR fact store
```

The phase does not decide which future collector to invoke.

## Every inference includes explanations

The production inference result contains local explanation information for every classifier for which the configured explanation method is supported.

There is no assumption that explanations are requested only for selected investigations.

The result must identify:

- classifier;
- model version;
- feature schema version;
- explanation method;
- feature value;
- per-feature contribution;
- base/reference value where applicable;
- output class/target to which contributions refer.

For multiclass models, contributions must be attributable to a specific output class.

Example:

```json
{
  "classifier": "threat-classifier",
  "model_version": "17",
  "target": "phishing",
  "method": "shap",
  "features": [
    {"name": "form_count", "value": 2, "contribution": 0.31},
    {"name": "external_script_ratio", "value": 0.91, "contribution": 0.22}
  ]
}
```

## Explanation completeness

If a model's explanation method cannot provide an exact per-feature attribution, the classifier must declare the limitation explicitly. The service must not fabricate SHAP values or silently omit the explanation.

For supported models, SHAP is the default local explanation strategy.

## Result retention

The classification pipeline returns the explanation. A later explainability module may store, aggregate, visualize or combine it with other evidence. That module is outside this project.

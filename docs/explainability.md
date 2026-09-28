# Explainability

## Requirement

Every production inference should carry local explanation data because a later explainability module will consume it.

The explanation is part of the classifier result, not a separate on-demand `/explain` operation.

## SHAP

SHAP is the default local explanation framework where the model family has a supported SHAP explainer.

The project should provide adapters for the model families actually used, for example:

- tree-based models;
- linear models;
- neural models;
- kernel/black-box models where practical.

"SHAP for everything" is a target interface, not a promise that every possible future model can produce mathematically equivalent SHAP explanations. If a model cannot support the required method, model registration must fail unless an explicitly approved alternative explanation contract is declared.

## Local explanation

For each inference:

```json
{
  "method": "shap",
  "target": "phishing",
  "base_value": 0.11,
  "output_value": 0.96,
  "features": [
    {
      "name": "external_script_ratio",
      "value": 0.91,
      "contribution": 0.42
    }
  ]
}
```

For multiclass models, one explanation vector is associated with each relevant output class, or the configuration explicitly chooses a target class.

## Global explanation

Training/evaluation produces:

- native gain when the model exposes it;
- mean absolute SHAP importance;
- feature-importance table;
- SHAP summary artifacts.

Do not invent "gain" for a model family that has no native gain concept.

## Non-ML detectors

For similarity/fingerprint detectors, explanation may be domain-specific:

```json
{
  "method": "fingerprint_similarity",
  "target": "phishing",
  "components": [
    {"name": "form_structure_similarity", "contribution": 0.51},
    {"name": "dom_tree_similarity", "contribution": 0.31}
  ],
  "nearest_templates": ["template-123", "template-982"]
}
```

The same result contract still applies: identify what evidence contributed to the output.

## Performance

Because explanations are mandatory in inference, explanation latency must be measured separately from prediction latency.

A model cannot be accepted solely because its prediction is fast if its required explanation is operationally unusable.

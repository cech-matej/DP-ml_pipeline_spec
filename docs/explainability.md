# Explainability

## Request-time explainability

Explainability is optional per service request, but it uses the same classification route and the same classifier implementation.

The request flag is:

```json
"include_explanations": true
```

When false, the service performs classification without running the local explanation step. When true, the response includes the configured local explanation for each classifier that supports the declared explanation contract.

This enables an empirical comparison between:

- **eager mode:** explain every classification and retain the explanations for THOR V2;
- **on-demand mode:** classify normally and re-run selected domains later with `include_explanations: true`.

The project does not assume either strategy is universally better. Prediction latency, explanation latency, storage volume, repeat-classification cost and workload shape should be measured.

## SHAP

SHAP is the default local explanation framework where the model family has a supported SHAP explainer.

The project should provide adapters for the model families actually used, for example:

- tree-based models;
- linear models;
- neural models;
- kernel/black-box models where practical.

"SHAP for everything" is a target interface, not a promise that every possible future model can produce mathematically equivalent SHAP explanations. If a model cannot support the required method, model registration must fail unless an explicitly approved alternative explanation contract is declared.

## Local explanation

For each requested inference:

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

## Performance measurement

Prediction and explanation timing should be measured separately. A request with explanations should expose enough internal metrics to compare classification-only execution with classification-plus-explanation execution.

For the eager-vs-on-demand experiment, record at least:

- classification latency;
- explanation latency;
- end-to-end latency;
- explanation storage size;
- number of repeated classifications for on-demand explanations;
- total compute consumed by each strategy.

The later THOR V2 explainability system is outside this project; this project only defines and optionally returns the local explanation payload.

# Feature schema and reusable extraction

## 1. One source of truth

Feature names, types, ordering and missing-value semantics live in one versioned feature-vector file.

Example:

```yaml
schema:
  name: html-js
  version: 5
  availability_boundary: html

features:
  - name: script_count
    type: float32
    nullable: false
    source: html

  - name: external_script_ratio
    type: float32
    nullable: false
    source: html

  - name: form_count
    type: int32
    nullable: false
    source: html
```

The schema file is the authoritative declaration of the feature-vector contract. Types must not be copied into classifier configs or duplicated as manually maintained Python lists.

**The YAML configuration also controls which features are extracted.** The Python extractor may implement all supported features, but only features listed under `features` in the loaded YAML configuration are calculated and returned. Features implemented in Python but not declared in the active YAML schema must not be invoked or extracted.

This allows different schema versions to select different subsets of the same extractor's supported features without requiring a separate extractor implementation for each version.

## 2. Feature-schema YAML reference

The feature configuration has two levels: `schema` describes the feature-vector contract as a whole, while each item under `features` describes one model input. The entries under `features` also determine which feature calculations are enabled.

### `schema.name`

Stable logical name of the feature schema. It identifies the feature definition independently of a particular classifier. For example, `html-js` identifies the HTML/JavaScript feature set.

### `schema.version`

Integer version of the feature schema. Increment it when model-visible semantics change, such as adding/removing a feature, changing its type, units, preprocessing, encoding, normalization or meaning.

A classifier should refer to the immutable schema identity such as `html-js-v5`.

### `schema.availability_boundary`

The minimum **information boundary** that must be available before the complete feature schema can be extracted. In `html-js-v5`, `html` means the phase must receive the HTML information before this feature vector can be produced.

This is intentionally different from `features[].source`: `source` says where an individual feature is derived from; `availability_boundary` says what complete input boundary is required by the schema as a whole.

Example: if a future schema contains five features derived from HTML and two derived from TLS, its boundary could be `html+tls` (or another explicitly defined boundary name), while individual features would still declare `source: html` or `source: tls`.

If every feature has the same source, the two fields may contain the same value, but they still describe different concepts.

### `features[].name`

Stable machine-readable feature name. This is the key used by the extractor output, validation layer, training data and model input mapping. Renaming it is a schema change.

Only feature names listed in the loaded YAML schema are part of that extraction run's output. A feature may be implemented in Python without being enabled in a particular schema version.

### `features[].type`

Runtime/data type expected by the feature vector, for example `int32`, `float32` or `string`. The extractor must return a value compatible with this declaration.

The type is defined only here; it must not be separately maintained in classifier configuration.

### `features[].nullable`

Whether the feature may contain a null/missing value. `false` means the extractor must provide a valid value and validation must reject null.

### `features[].source`

The information source from which this particular feature is computed. Examples are `html` and `dom`. It describes feature provenance, not when the whole schema becomes available.

`source` is deliberately per-feature because one schema may eventually combine features from multiple information sources.

## 3. Extractor implementation and selective extraction

An extractor should implement the calculation logic for all supported features, but it must not calculate every supported feature unconditionally. The loaded feature schema determines which calculations are needed for a particular extraction run.

For example:

```python
class HtmlJsExtractor:
    def __init__(self, schema):
        self.schema = schema

    def extract(self, source: HtmlInput) -> FeatureVector:
        requested = {feature.name for feature in self.schema.features}
        values = {}

        if "script_count" in requested:
            values["script_count"] = count_scripts(source)

        if "external_script_ratio" in requested:
            values["external_script_ratio"] = external_script_ratio(source)

        if "form_count" in requested:
            values["form_count"] = count_forms(source)

        return self.schema.validate(values)
```

This example illustrates the selection rule; the production extractor should use its shared implementation and schema-driven feature selection.

The important requirements are:

- The YAML schema determines which features are requested.
- The Python extractor defines how each supported feature is calculated.
- A calculation is invoked only if its feature is requested by the active schema.
- Features not declared in the active YAML schema are not calculated, returned or passed to the classifier.
- Shared intermediate calculations may be reused when multiple requested features depend on them, but must not trigger unrelated feature calculations.
- Output feature names, types and ordering must match the loaded schema.

The extractor does not contain a second declaration such as `script_count: float32`. Its output is validated against the schema, which remains the authoritative source of truth.

## 4. Runtime enforcement

`schema.validate()` must fail loudly when:

- a required feature is missing;
- an undeclared feature is returned;
- a feature has the wrong runtime type;
- a value violates nullability;
- a categorical value is outside the declared vocabulary, when a vocabulary is defined;
- ordering or shape is incompatible;
- the required `availability_boundary` is not satisfied.

Only the features declared in the loaded schema are expected in the feature vector. Implementing additional features in Python does not make them part of the active schema.

Use a generated typed model internally if desired, but the generated model is derived from the schema and must not become a second hand-maintained source of truth.

Example failure:

```text
FeatureSchemaMismatch:
  schema=html-js-v5
  feature=form_count
  expected_type=int32
  actual_type=str
```

## 5. Training, inference and standalone extraction reuse

There must be exactly one production implementation of an extractor. Training, inference and standalone feature extraction must reuse the same feature calculation logic and load the appropriate feature schema.

```text
training from raw data
  -> shared extractor
  -> calculate only YAML-selected features
  -> schema.validate(...)
  -> training

standalone feature extraction
  -> shared extractor
  -> calculate only YAML-selected features
  -> schema.validate(...)
  -> persist feature-extracted dataset

training from pre-extracted data
  -> load existing feature-extracted dataset
  -> validate compatibility with the selected schema
  -> train without recalculating features

inference
  -> shared extractor
  -> calculate only YAML-selected features
  -> schema.validate(...)
  -> classifier
```

Standalone extraction allows a large dataset to be processed once and reused for multiple training runs. The training script should provide an explicit option to indicate that the input dataset already contains extracted features, so it can skip extraction.

When using a pre-extracted dataset, the dataset must contain all features required by the selected schema, with compatible types and semantics. The feature schema version used to create the dataset must be compatible with the version expected by training.

Do not create separate training and inference implementations of the same feature calculations.

## 6. Feature versioning

Create a new schema version when model-visible semantics change:

- feature added or removed from the schema;
- type changed;
- units changed;
- preprocessing changed;
- normalization changed;
- encoding changed;
- missing-value semantics changed;
- feature meaning changed.

The Python extractor can support features beyond those selected by a particular schema version. Adding an implementation for a new optional feature does not by itself require changing an existing schema, provided it does not change the behavior of existing features.

When a feature is added to a schema, the extractor must support its calculation. When a feature is removed from a schema, its calculation should no longer be invoked for that schema version unless it is also needed as a shared dependency of another selected feature.

Record the feature schema name and version, extractor implementation version or revision, and relevant extraction assets in W&B metadata. This helps identify how a feature-extracted dataset and trained model were produced.

## 7. Current feature schemas

### `config/features/example_html-js.yaml`

- `schema.name`: `html-js`
- `schema.version`: `5`
- `schema.availability_boundary`: `html`
- `script_count`: `float32`, required, derived from `html`
- `external_script_ratio`: `float32`, required, derived from `html`
- `form_count`: `int32`, required, derived from `html`
- `inline_js_entropy`: `float32`, required, derived from `html`

Only these declared features are extracted when this schema version is loaded. Other HTML/JavaScript features supported by the Python extractor remain inactive unless they are added to a feature schema.

### `config/features/example_dom-fingerprint.yaml`

- `schema.name`: `dom-fingerprint`
- `schema.version`: `2`
- `schema.availability_boundary`: `html`
- `dom_node_count`: `int32`, required, derived from `dom`
- `dom_depth`: `int32`, required, derived from `dom`
- `form_structure_hash`: `string`, required, derived from `dom`
- `phishing_template_similarity`: `float32`, required, derived from `dom`

Only the features declared in this schema are extracted when it is loaded.

Notice that the DOM feature schema has an `html` availability boundary even though its individual feature `source` is `dom`. This means `html` is the declared input/information boundary at which the DOM representation is available to the phase; `dom` identifies the derived representation used by those features.

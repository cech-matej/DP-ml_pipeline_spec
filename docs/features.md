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

The schema file is the authoritative declaration of feature types. Types must not be copied into classifier configs or duplicated as manually maintained Python lists.

## 2. Feature-schema YAML reference

The feature configuration has two levels: `schema` describes the feature-vector contract as a whole, while each item under `features` describes one model input.

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

### `features[].type`

Runtime/data type expected by the feature vector, for example `int32`, `float32` or `string`. The extractor must return a value compatible with this declaration.

The type is defined only here; it must not be separately maintained in classifier configuration.

### `features[].nullable`

Whether the feature may contain a null/missing value. `false` means the extractor must provide a valid value and validation must reject null.

### `features[].source`

The information source from which this particular feature is computed. Examples are `html` and `dom`. It describes feature provenance, not when the whole schema becomes available.

`source` is deliberately per-feature because one schema may eventually combine features from multiple information sources.

## 3. Extractor implementation

An extractor should compute values, not redefine their schema:

```python
class HtmlJsExtractor:
    schema = load_feature_schema("html-js-v5")

    def extract(self, source: HtmlInput) -> FeatureVector:
        values = {
            "script_count": count_scripts(source),
            "external_script_ratio": external_script_ratio(source),
            "form_count": count_forms(source),
        }
        return self.schema.validate(values)
```

The extractor does not contain a second declaration such as `script_count: float32`.

## 4. Runtime enforcement

`schema.validate()` must fail loudly when:

- a required feature is missing;
- an undeclared feature is returned;
- a feature has the wrong runtime type;
- a value violates nullability;
- a categorical value is outside the declared vocabulary;
- ordering/shape is incompatible;
- the required `availability_boundary` is not satisfied.

Use a generated typed model internally if desired, but the generated model is derived from the schema and must not become a second hand-maintained source of truth.

Example failure:

```text
FeatureSchemaMismatch:
  schema=html-js-v5
  feature=form_count
  expected_type=int32
  actual_type=str
```

## 5. Training and inference reuse

There must be exactly one production implementation of an extractor.

```text
training
  -> extractor.extract(...)
  -> schema.validate(...)
  -> feature dataset

inference
  -> extractor.extract(...)
  -> schema.validate(...)
  -> classifier
```

Do not create a separate "training feature script" and "inference feature script".

## 6. Feature versioning

Create a new schema version when model-visible semantics change:

- feature added/removed;
- type changed;
- units changed;
- preprocessing changed;
- normalization changed;
- encoding changed;
- missing-value semantics changed;
- meaning changed.

The extractor implementation and schema version are recorded together in W&B metadata.

## 7. Current feature schemas

### `configs/features/html-js-v5.yaml`

- `schema.name`: `html-js`
- `schema.version`: `5`
- `schema.availability_boundary`: `html`
- `script_count`: `float32`, required, derived from `html`
- `external_script_ratio`: `float32`, required, derived from `html`
- `form_count`: `int32`, required, derived from `html`
- `inline_js_entropy`: `float32`, required, derived from `html`

### `configs/features/dom-fingerprint-v2.yaml`

- `schema.name`: `dom-fingerprint`
- `schema.version`: `2`
- `schema.availability_boundary`: `html`
- `dom_node_count`: `int32`, required, derived from `dom`
- `dom_depth`: `int32`, required, derived from `dom`
- `form_structure_hash`: `string`, required, derived from `dom`
- `phishing_template_similarity`: `float32`, required, derived from `dom`

Notice that the DOM feature schema has an `html` availability boundary even though its individual feature `source` is `dom`. This means `html` is the declared input/information boundary at which the DOM representation is available to the phase; `dom` identifies the derived representation used by those features.

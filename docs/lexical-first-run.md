# Lexical classifier: first runnable pipeline

## 1. Install

Python 3.11+ is required. From the repository root:

```bash
python -m pip install -e ".[dev,serving]"
```

## 2. Prepare data and train

Create a CSV or Parquet dataset containing `domain_name` and `label`. Labels must be `benign`, `malware`, `phishing`, or `dga`.

```bash
python training/models/lexical/train.py --dataset data/domains.csv
```

The training command writes `artifacts/lexical/model.joblib`. The feature extractor is shared between training and inference. The versioned feature config is `config/features/lexical/v1.yaml`.

## 3. Start HTTP

```bash
python scripts/run_lexical_http.py
```

The default listener is `127.0.0.1:8080`. Set `LEXICAL_MODEL_PATH` if the model artifact is elsewhere. Set `LEXICAL_DATA_DIR` if n-gram JSON assets are elsewhere.

## 4. Send a batch request

The HTTP route is `POST /predict`. Example request body:

```json
{
  "include_explanations": false,
  "domains": [
    {
      "domain_id": "www.example.com",
      "facts": {
        "lexical": {
          "domain_name": "www.example.com"
        }
      }
    },
    {
      "domain_id": "verify-account-login.test",
      "facts": {
        "lexical": {
          "domain_name": "verify-account-login.test"
        }
      }
    }
  ]
}
```

`domain_id` identifies a domain within this request and must be unique in the batch. `facts.lexical.domain_name` is the input to the lexical extractor. `include_explanations` controls whether the response contains local explanation data.

Try `GET /health` first. This endpoint will fail to start if no trained model artifact exists; that is intentional, since a classifier should not silently serve untrained predictions.

## 5. Run tests and validate configs

```bash
python -m pytest
python scripts/validate_configs.py
```

## Important limitations of this first implementation

- The explanation is an importance-weighted feature ranking, not SHAP and not a signed causal attribution. It is explicitly labelled accordingly in responses. Replace it with SHAP before relying on explanations for analyst decisions.
- The initial model is a Random Forest baseline. Compare per-class precision/recall, confusion matrix, calibration and false-positive/false-negative rates before deployment.

## Reuse extracted features across training runs

The feature YAML is the allow-list for a feature version: `LexicalExtractor` computes only the feature names declared in the loaded schema. Features implemented in `src/domain_detection/features/lexical.py` but omitted from that YAML are not computed or returned.

Extract once to a reusable dataset:

```bash
python training/models/lexical/extract_features.py \
  --dataset data/domains.csv \
  --output data/domains-lexical-v1.parquet \
  --feature-config config/features/lexical/v1.yaml \
  --batch-size 10000
```

Then train repeatedly without rerunning feature extraction:

```bash
python training/models/lexical/train.py \
  --dataset data/domains-lexical-v1.parquet \
  --features-extracted \
  --feature-config config/features/lexical/v1.yaml \
  --n-estimators 300
```

The pre-extracted file must contain `domain_name`, `label`, and every feature column configured in the selected YAML version. Reuse it only with the same feature schema/version and compatible extraction assets (including the n-gram JSON files when those features are enabled). Without `--features-extracted`, training retains the existing behavior and extracts features itself.

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

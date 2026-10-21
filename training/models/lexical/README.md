# Lexical classifier

## Dataset contract

Supply a versioned CSV or Parquet file with these columns:

- `domain_name`: domain string, such as `login-example.test`
- `label`: exactly one of `benign`, `malware`, `phishing`, `dga`

The training entry point uses the same `LexicalExtractor` and `config/features/lexical/v1.yaml` schema as inference. The training script does not modify the source dataset.

## Train

From the repository root, install the project and optional serving dependencies:

```bash
python -m pip install -e ".[dev,serving]"
python training/models/lexical/train.py --dataset data/domains.csv
```

Or use Parquet:

```bash
python training/models/lexical/train.py --dataset data/domains.parquet
```

The model is written to `artifacts/lexical/model.joblib`, with metrics alongside it. The dataset must have enough examples in every class for a stratified train/test split. Use real labelled data; do not treat synthetic examples as a quality evaluation.

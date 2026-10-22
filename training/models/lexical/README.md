# Lexical classifier

## Dataset contract

Supply a versioned CSV or Parquet file with these columns:

- `domain_name`: domain string, such as `login-example.test`
- `label`: exactly one of `benign`, `malware`, `phishing`, `dga`

The training entry point uses the same `LexicalExtractor` and `config/features/lexical/v1.yaml` schema as inference. The training script does not modify the source dataset.

## Install dependencies

From the repository root, install the project and optional serving dependencies:

```bash
python -m pip install -e ".[dev,serving]"
```

## Extract features

Feature extraction can be run independently of training. This lets you extract features once and reuse the resulting dataset for multiple training runs.

For example, to extract features from a CSV dataset and save the result as Parquet:

```bash
python training/models/lexical/extract_features.py \
  --dataset data/domains.csv \
  --output data/domains-lexical-v1.parquet \
  --feature-config config/features/lexical/v1.yaml \
  --batch-size 10000
```

The input dataset must contain the columns described in the dataset contract. The output contains the original `domain_name` and `label` columns, along with the extracted feature columns.

The feature configuration determines which features are extracted. Features not specified in the selected YAML configuration are not calculated.

You can also use Parquet as the input:

```bash
python training/models/lexical/extract_features.py \
  --dataset data/domains.parquet \
  --output data/domains-lexical-v1.parquet \
  --feature-config config/features/lexical/v1.yaml \
  --batch-size 10000
```

Choose an output filename that identifies the feature schema version. Keep the feature configuration and any required extraction assets consistent with the dataset you produce.

## Train with feature extraction

By default, the training script extracts features from the source dataset before training.

For CSV:

```bash
python training/models/lexical/train.py \
  --dataset data/domains.csv
```

For Parquet:

```bash
python training/models/lexical/train.py \
  --dataset data/domains.parquet
```

The training script uses the configured feature schema and extracts features in batches.

## Train without feature extraction

If you have already generated a feature-extracted dataset, pass the `--features-extracted` flag to skip feature extraction:

```bash
python training/models/lexical/train.py \
  --dataset data/domains-lexical-v1.parquet \
  --features-extracted \
  --feature-config config/features/lexical/v1.yaml \
  --n-estimators 300
```

This is useful when experimenting with model parameters or retraining models on the same dataset. Features are calculated only once, rather than every time training runs.

**Important:** The pre-extracted dataset must contain all features required by the selected feature configuration, with compatible values and types. Use the matching feature schema version when training.

## Training outputs and evaluation

The model is written to `artifacts/lexical/model.joblib`, with metrics alongside it.

The dataset must have enough examples in every class for a stratified train/test split. Use real labelled data; do not treat synthetic examples as a quality evaluation.

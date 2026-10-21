"""Train the lexical multiclass classifier from a labelled CSV/Parquet dataset."""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import joblib
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from tqdm import tqdm

from domain_detection.features.contracts import FeatureSchema
from domain_detection.features.lexical import LexicalExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


def load_dataset(path: Path) -> pd.DataFrame:
    """Load the labelled source dataset.

    :param path: CSV or Parquet path with ``domain_name`` and ``label`` columns.
    :return: Dataset dataframe.
    """
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError("Dataset must be CSV or Parquet")


def main() -> None:
    """Parse CLI arguments, extract features, train, evaluate, and save the model."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path, help="CSV/Parquet with domain_name,label")
    parser.add_argument("--feature-config", type=Path, default=Path("config/features/lexical/v1.yaml"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/lexical/model.joblib"))
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Optional n-gram JSON directory")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=10_000, help="Domains processed per extraction batch")
    parser.add_argument("--n-estimators", type=int, default=300, help="Number of Random Forest trees")
    args = parser.parse_args()
    started = time.perf_counter()

    def log_elapsed(message: str) -> None:
        logger.info("[%7.1fs elapsed] %s", time.perf_counter() - started, message)

    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    log_elapsed(f"Loading feature config from {args.feature_config}")
    config = yaml.safe_load(args.feature_config.read_text(encoding="utf-8"))
    schema_cfg = config["schema"]
    schema = FeatureSchema(schema_cfg["name"], schema_cfg["version"], config["features"])
    extractor = LexicalExtractor(schema, args.data_dir)
    feature_names = [feature["name"] for feature in config["features"]]
    logger.info("Feature schema: %s v%s | %d features", schema.name, schema.version, len(feature_names))

    log_elapsed(f"Loading dataset from {args.dataset}")
    dataset = load_dataset(args.dataset)
    log_elapsed(f"Dataset loaded: {len(dataset):,} rows")
    required = {"domain_name", "label"}
    if not required.issubset(dataset.columns):
        raise ValueError(f"Dataset must contain columns: {sorted(required)}")
    before_drop = len(dataset)
    dataset = dataset.dropna(subset=["domain_name", "label"]).copy().reset_index(drop=True)
    log_elapsed(f"Removed {before_drop - len(dataset):,} rows with missing values")
    allowed = {"benign", "malware", "phishing", "dga"}
    dataset["label"] = dataset["label"].astype(str)
    unknown = set(dataset["label"]) - allowed
    if unknown:
        raise ValueError(f"Unknown labels {sorted(unknown)}; expected {sorted(allowed)}")
    logger.info("Label distribution:\n%s", dataset["label"].value_counts().to_string())

    log_elapsed(f"Starting extraction in batches of {args.batch_size:,}")
    batches = []
    total = len(dataset)
    with tqdm(total=total, desc="Extracting lexical features", unit="domain", dynamic_ncols=True) as progress:
        for start in range(0, total, args.batch_size):
            domain_batch = dataset.iloc[start:start + args.batch_size]["domain_name"]
            batch_features = extractor.extract_batch(domain_batch)
            batches.append(batch_features)
            progress.update(len(domain_batch))
    X = pd.concat(batches, ignore_index=True) if batches else pd.DataFrame(columns=feature_names)
    X = X.loc[:, feature_names]
    y = dataset["label"].reset_index(drop=True)
    log_elapsed(f"Feature extraction complete: X={X.shape}, y={y.shape}")

    log_elapsed("Splitting dataset")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.random_state, stratify=y
    )
    log_elapsed(f"Split complete: train={len(X_train):,}, test={len(X_test):,}")
    model = RandomForestClassifier(
        n_estimators=args.n_estimators, class_weight="balanced", random_state=args.random_state,
        n_jobs=-1, min_samples_leaf=2, verbose=1,
    )
    log_elapsed(f"Starting Random Forest training ({args.n_estimators} trees)")
    model.fit(X_train, y_train)
    log_elapsed("Random Forest training complete")
    predictions = model.predict(X_test)
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "f1_weighted": float(f1_score(y_test, predictions, average="weighted")),
        "classification_report": classification_report(y_test, predictions, output_dict=True, zero_division=0),
    }
    log_elapsed(f"Evaluation complete: accuracy={metrics['accuracy']:.4f}, weighted F1={metrics['f1_weighted']:.4f}")
    artifact = {
        "model": model, "feature_names": list(X.columns), "version": 1,
        "feature_schema": {"name": schema.name, "version": schema.version},
        "metrics": metrics, "random_state": args.random_state,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_elapsed(f"Saving model to {args.output}")
    joblib.dump(artifact, args.output)
    metrics_path = args.output.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    log_elapsed(f"Saved metrics to {metrics_path}; training pipeline finished")
    print(json.dumps({"model": str(args.output), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()

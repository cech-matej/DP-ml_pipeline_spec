"""Train a lexical multiclass classifier using a labelled CSV or Parquet dataset

The training pipeline performs the following steps:
1. Load the feature configuration and initialize the lexical feature extractor
2. Load and validate the labelled dataset
3. Extract lexical features or load pre-extracted feature columns
4. Split the dataset into stratified training and testing sets
5. Train a class-balanced Random Forest classifier
6. Evaluate the model using accuracy, weighted F1, and a classification report
7. Save the trained model, feature metadata, and evaluation metrics

The resulting model artifact contains the classifier, feature names, schema
version, evaluation metrics, and random state required for reproducibility
"""

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


# Configure consistent logging for tracking the progress of the training pipeline
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


def load_dataset(path: Path) -> pd.DataFrame:
    """Load a dataset from a supported CSV or Parquet file
    
    The input format is determined from the file extension, allowing the
    caller to use the same function for either supported format

    CSV files are loaded using pandas' CSV reader, while Parquet files
    are loaded using pandas' Parquet reader

    :param path: Path to the input dataset file
    :return: A DataFrame containing the loaded dataset
    :raises ValueError: If the file extension is not CSV or Parquet
    """

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    
    raise ValueError("Dataset must be CSV or Parquet")


def main() -> None:
    """Execute the complete lexical classification training pipeline.

    The pipeline loads the feature configuration and labelled dataset,
    validates the input data, and prepares the lexical feature matrix.
    Features are either extracted from domain names in batches or loaded
    directly from a dataset containing pre-extracted feature columns.

    The prepared dataset is split into stratified training and testing
    subsets. A class-balanced Random Forest classifier is trained on the
    training subset and evaluated on the held-out testing subset using
    accuracy, weighted F1-score, and a classification report.

    The trained model, feature metadata, and evaluation metrics are saved
    to the configured output location. Evaluation metrics are also written
    to a separate JSON file for convenient inspection and further analysis.

    Command-line arguments control the dataset location, feature
    configuration, output paths, extraction batch size, test set
    proportion, random seed, and number of trees in the classifier.

    :raises ValueError: If the dataset is missing required columns, contains
        unsupported labels, or lacks configured pre-extracted features
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path, help="CSV/Parquet with domain_name,label")
    parser.add_argument("--feature-config", type=Path, default=Path("config/features/lexical/v1.yaml"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/lexical/model.joblib"))
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Optional n-gram JSON directory")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=10_000, help="Rows processed per extraction batch")
    parser.add_argument("--features-extracted", action="store_true", help="Input dataset already contains the configured feature columns; skip extraction")
    parser.add_argument("--n-estimators", type=int, default=300, help="Number of Random Forest trees")

    args = parser.parse_args()

    # Record the start time using a high-resolution performance counter
    started = time.perf_counter()

    def log_elapsed(message: str) -> None:
        """Log a progress message together with total elapsed time

        :param message: Description of the current pipeline stage
        """

        logger.info("[%7.1fs elapsed] %s", time.perf_counter() - started, message)

    # Reject invalid batch sizes before starting data processing
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    # Load the YAML configuration that defines the feature schema
    log_elapsed(f"Loading feature config from {args.feature_config}")
    config = yaml.safe_load(args.feature_config.read_text(encoding="utf-8"))

    # Build the schema contract and initialize the feature extractor
    schema_cfg = config["schema"]
    schema = FeatureSchema(schema_cfg["name"], schema_cfg["version"], config["features"])
    extractor = LexicalExtractor(schema, args.data_dir)
    feature_names = [feature["name"] for feature in config["features"]]
    logger.info("Feature schema: %s v%s | %d features", schema.name, schema.version, len(feature_names))

    # Load the dataset and verify that the required columns are present
    log_elapsed(f"Loading dataset from {args.dataset}")
    dataset = load_dataset(args.dataset)
    log_elapsed(f"Dataset loaded: {len(dataset):,} rows")

    required = {"domain_name", "label"}
    if not required.issubset(dataset.columns):
        raise ValueError(f"Dataset must contain columns: {sorted(required)}")

    # Remove rows that cannot be used for supervised learning because either
    # the domain name or its corresponding target label is missing
    before_drop = len(dataset)
    dataset = dataset.dropna(subset=["domain_name", "label"]).copy().reset_index(drop=True)
    log_elapsed(f"Removed {before_drop - len(dataset):,} rows with missing values")

    # Normalize labels to strings and reject values outside the supported
    # classification categories
    allowed = {"benign", "malware", "phishing", "dga"}
    dataset["label"] = dataset["label"].astype(str)
    unknown = set(dataset["label"]) - allowed

    if unknown:
        raise ValueError(f"Unknown labels {sorted(unknown)}; expected {sorted(allowed)}")

    # Report class counts to help identify class imbalance in the dataset
    logger.info("Label distribution:\n%s", dataset["label"].value_counts().to_string())

    # Prepare the feature matrix
    # Either use existing feature columns or calculate the lexical features from the domain names
    if args.features_extracted:
        # Skip extraction when the input already contains every configured feature
        log_elapsed("Using pre-extracted feature columns; skipping extraction")

        missing_features = set(feature_names) - set(dataset.columns)
        if missing_features:
            raise ValueError(f"Pre-extracted dataset is missing configured feature columns: {sorted(missing_features)}")

        # Select only configured features and create an independent DataFrame
        X = dataset.loc[:, feature_names].copy()

        # Enforce numeric types declared by the feature configuration
        for feature in config["features"]:
            name = feature["name"]
            X[name] = pd.to_numeric(X[name], errors="raise")

            if feature["type"].startswith("int"):
                X[name] = X[name].astype("int64")
            elif feature["type"].startswith("float"):
                X[name] = X[name].astype("float64")
    else:
        # Extract features in batches to limit the amount of data processed
        # in a single operation and display progress for large datasets
        log_elapsed(f"Starting extraction in batches of {args.batch_size:,}")

        batches = []
        total = len(dataset)

        with tqdm(total=total, desc="Extracting lexical features", unit="domain", dynamic_ncols=True) as progress:
            for start in range(0, total, args.batch_size):
                # Select the domain names for the current batch
                domain_batch = dataset.iloc[start:start + args.batch_size]["domain_name"]

                # Calculate the configured lexical features for each domain
                batch_features = extractor.extract_batch(domain_batch)
                batches.append(batch_features)

                # Update the progress bar by the number of processed domains
                progress.update(len(domain_batch))

        # Combine all extracted batches while preserving row order
        # Handle an empty dataset by creating an empty feature matrix
        X = pd.concat(batches, ignore_index=True) if batches else pd.DataFrame(columns=feature_names)

        # Keep only the configured features in their expected order
        X = X.loc[:, feature_names]

    # The target vector must remain aligned with the feature matrix
    y = dataset["label"].reset_index(drop=True)
    log_elapsed(f"Features ready: X={X.shape}, y={y.shape}")

    # Split the data into training and testing sets
    log_elapsed("Splitting dataset")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.random_state, stratify=y
    )

    # Configure a Random Forest classifier
    log_elapsed(f"Split complete: train={len(X_train):,}, test={len(X_test):,}")
    model = RandomForestClassifier(
        n_estimators=args.n_estimators, class_weight="balanced", random_state=args.random_state,
        n_jobs=-1, min_samples_leaf=2, verbose=1,
    )

    # Fit the classifier using only the training subset
    log_elapsed(f"Starting Random Forest training ({args.n_estimators} trees)")
    model.fit(X_train, y_train)

    # Generate predictions for the held-out test subset
    log_elapsed("Random Forest training complete")
    predictions = model.predict(X_test)

    # Calculate overall accuracy, class-frequency-weighted F1, and
    # per-class evaluation metrics. Convert accuracy and F1 to native
    # Python floats so the metrics can be serialized to JSON.
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "f1_weighted": float(f1_score(y_test, predictions, average="weighted")),
        "classification_report": classification_report(y_test, predictions, output_dict=True, zero_division=0),
    }
    log_elapsed(f"Evaluation complete: accuracy={metrics['accuracy']:.4f}, weighted F1={metrics['f1_weighted']:.4f}")

    # Package the classifier with the metadata required to interpret its
    # feature inputs and track the configuration used during training
    artifact = {
        "model": model,
        "feature_names": list(X.columns),
        "version": 1,
        "feature_schema": {
            "name": schema.name,
            "version": schema.version
        },
        "metrics": metrics,
        "random_state": args.random_state,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Serialize the trained model and metadata into a reusable Joblib artifact
    log_elapsed(f"Saving model to {args.output}")
    joblib.dump(artifact, args.output)

    # Save evaluation metrics separately as a human-readable JSON file
    metrics_path = args.output.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # Report completion and print a machine-readable summary
    log_elapsed(f"Saved metrics to {metrics_path}; training pipeline finished")
    print(json.dumps({"model": str(args.output), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()

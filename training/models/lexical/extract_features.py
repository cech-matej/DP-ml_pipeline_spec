"""Create a reusable feature-extracted CSV/Parquet dataset for lexical training.

This script reads a dataset containing domain names and their labels,
extracts lexical features for each domain, and saves the resulting dataset
in CSV or Parquet format.

The feature extraction process uses a YAML configuration to define the
feature schema and a lexical extractor to calculate the configured features.
Processing is performed in batches to help manage memory usage when working
with large datasets.

The output dataset contains the original domain names and labels, together
with the extracted feature columns. It can then be reused for training
and evaluating lexical classification models without repeating feature
extraction.
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import pandas as pd
import yaml
from tqdm import tqdm

from domain_detection.features.contracts import FeatureSchema
from domain_detection.features.lexical import LexicalExtractor


# Configure the root logger to display informational messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S")

# Create a module-level logger for reporting dataset processing progress
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
    
    raise ValueError("Input dataset must be CSV or Parquet")


def main() -> None:
    """Extract lexical features from a dataset and save the enriched data

    The function performs the following steps:
        1. Parses command-line arguments
        2. Validates the batch size
        3. Loads the feature configuration and constructs the feature schema
        4. Initializes the lexical feature extractor
        5. Loads and validates the input dataset
        6. Removes rows with missing domain names or labels
        7. Extracts lexical features in batches
        8. Combines the original columns with the extracted features
        9. Saves the resulting dataset in CSV or Parquet format
        10. Logs the output dimensions and total processing time

    The input dataset must contain the columns "domain_name" and "label"
    The output format is determined by the output file extension

    :raises ValueError: If the dataset is missing required columns or
        the output file extension is unsupported
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path, help="Input CSV/Parquet with domain_name and label")
    parser.add_argument("--output", required=True, type=Path, help="Output CSV/Parquet path")
    parser.add_argument("--feature-config", type=Path, default=Path("config/features/lexical/v1.yaml"))
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Directory containing optional n-gram JSON files")
    parser.add_argument("--batch-size", type=int, default=10_000)

    args = parser.parse_args()

    # Ensure that the batch size is positive
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    # Reject unsupported output extensions so the script does not
    # silently write data in an unexpected format
    if args.output.suffix.lower() not in {".csv", ".parquet", ".pq"}:
        raise ValueError("Output path must end in .csv or .parquet/.pq")

    # Record the start time using a high-resolution performance counter
    started = time.perf_counter()

    # Read the feature configuration from YAML
    config = yaml.safe_load(args.feature_config.read_text(encoding="utf-8"))

    # Extract the schema metadata, including its name and version
    schema_cfg = config["schema"]

    # Create the FeatureSchema object from the configuration
    schema = FeatureSchema(schema_cfg["name"], schema_cfg["version"], config["features"])

    # Collect the configured feature names in their declared order
    feature_names = [item["name"] for item in config["features"]]

    # Initialize the lexical feature extractor
    extractor = LexicalExtractor(schema, args.data_dir)

    # Load the input dataset
    dataset = load_dataset(args.dataset)

    # Define the columns that must be present for feature extraction
    required = {"domain_name", "label"}

    if not required.issubset(dataset.columns):
        raise ValueError(f"Input dataset must contain columns: {sorted(required)}")

    # Remove rows where either the domain name or label is missing
    dataset = dataset.dropna(subset=["domain_name", "label"]).copy().reset_index(drop=True)

    # Log a summary of the extraction job before processing begins
    logger.info("Extracting %d rows using %s v%s (%d configured features)", len(dataset), schema.name, schema.version, len(feature_names))

    # Store the processed batches here
    chunks = []

    # Iterate over the dataset in batches to avoid processing all rows
    # in one large extraction operation
    for start in tqdm(range(0, len(dataset), args.batch_size), desc="Extracting features", unit="batch", dynamic_ncols=True):
        batch = dataset.iloc[start:start + args.batch_size]
        extracted = extractor.extract_batch(batch["domain_name"])
        chunks.append(pd.concat([batch[["domain_name", "label"]].reset_index(drop=True), extracted.reset_index(drop=True)], axis=1))

    # Combine all processed batches into one DataFrame
    result = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=["domain_name", "label", *feature_names])

    # Create the output file
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() == ".csv":
        result.to_csv(args.output, index=False)
    elif args.output.suffix.lower() in {".parquet", ".pq"}:
        result.to_parquet(args.output, index=False)

    # Calculate the total elapsed time and log a summary of the completed job
    logger.info("Saved %s with shape %s in %.1fs", args.output, result.shape, time.perf_counter() - started)


if __name__ == "__main__":
    main()

"""Run the lexical phase over HTTP using the versioned repository configs.

This script loads the configuration files required by the lexical phase,
initializes the feature extractor and classifier, and creates a phase runner.
It then starts an HTTP server using Uvicorn.

Configuration file paths and server settings can be overridden using
environment variables. The phase must use HTTP transport; Kafka transport
must be handled by a separate wrapper.
"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
import yaml

from domain_detection.classifiers.lexical import LexicalClassifier
from domain_detection.features.contracts import FeatureSchema
from domain_detection.features.lexical import LexicalExtractor
from domain_detection.phases.runner import PhaseRunner
from domain_detection.serving.http import create_app


def main() -> None:
    """Initialize the lexical phase and start its HTTP server.

    The function performs the following steps:
        1. Determines the repository root directory.
        2. Loads the phase, feature, and classifier configurations.
        3. Creates the feature schema and lexical feature extractor.
        4. Initializes the lexical classifier.
        5. Combines the components into a phase runner.
        6. Creates the HTTP application and validates the transport type.
        7. Starts the HTTP server using Uvicorn.

    Environment variables can override the default configuration paths,
    lexical data directory, and HTTP server host and port.
    """

    # Determine the repository root relative to this script's location
    # This allows the script to find configuration files and data regardless
    # of the directory from which it is executed
    root = Path(__file__).resolve().parents[1]

    # Resolve the configuration file paths.
    phase_config_path = Path(os.getenv("PHASE_CONFIG", root / "config/phases/example_lexical.yaml"))
    feature_config_path = Path(os.getenv("FEATURE_CONFIG", root / "config/features/lexical/v1.yaml"))
    classifier_config_path = Path(os.getenv("CLASSIFIER_CONFIG", root / "config/classifiers/lexical/v1.yaml"))

    # Load the phase configuration and select the "phase" section
    # This section defines the phase name, version, and execution settings
    phase_cfg = yaml.safe_load(phase_config_path.read_text(encoding="utf-8"))["phase"]

    # Load the feature configuration
    # It defines the feature schema and the features to be extracted
    feature_cfg = yaml.safe_load(feature_config_path.read_text(encoding="utf-8"))

    # Load the classifier configuration and select the "classifier" section
    # This section provides the classifier's configured name and settings
    classifier_cfg = yaml.safe_load(classifier_config_path.read_text(encoding="utf-8"))["classifier"]

    # Extract the schema metadata from the feature configuration
    # The schema identifies the feature set by its name and version
    schema_cfg = feature_cfg["schema"]

    # Create a feature schema describing the features produced by the extractor
    # The schema name and version help identify which feature definition
    # is being used by the lexical phase
    schema = FeatureSchema(schema_cfg["name"], schema_cfg["version"], feature_cfg["features"])

    # Initialize the lexical feature extractor
    # It uses the schema to determine which features to extract and the
    # configured data directory to access any required lexical resources
    extractor = LexicalExtractor(schema, os.getenv("LEXICAL_DATA_DIR", str(root / "data")))

    # Initialize the lexical classifier
    classifier = LexicalClassifier()

    # Associate the classifier with the feature schema it expects
    classifier.feature_schema = schema.name

    # Create the phase runner, which coordinates feature extraction
    # and classification for the lexical phase
    phase = PhaseRunner(
        name=phase_cfg["name"],
        version=str(phase_cfg["version"]),
        extractors={schema.name: extractor},
        classifiers={classifier_cfg["name"]: classifier},
        parallel_classifiers=phase_cfg.get("execution", {}).get("parallel_classifiers", False),
        max_concurrent_domains=phase_cfg.get("execution", {}).get("max_concurrent_domains", 4),
    )

    # Use the phase runner as an HTTP application
    app = create_app(phase)

    # Load the transport configuration from the phase configuration file
    transport = yaml.safe_load(phase_config_path.read_text(encoding="utf-8"))["transport"]

    # This script supports HTTP transport only
    # Fail early with a clear message if the configuration specifies Kafka
    # or another transport, rather than starting the wrong type of server
    if transport.get("type") != "http":
        raise ValueError("scripts/run_lexical_http.py only starts HTTP; use the Kafka wrapper for type: kafka")

    # Extract the HTTP-specific configuration
    http = transport["http"]

    # Start the HTTP server using Uvicorn
    uvicorn.run(app, host=os.getenv("HOST", http.get("host", "127.0.0.1")),
                port=int(os.getenv("PORT", http.get("port", 8080))))


if __name__ == "__main__":
    main()

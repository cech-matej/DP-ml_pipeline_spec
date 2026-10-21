"""Runtime adapter for the trained lexical multiclass classifier.

This module loads a persisted scikit-learn model and exposes a consistent
interface for making predictions, generating local feature explanations,
and retrieving model metadata.

The classifier expects a trained model artifact containing the estimator
and its corresponding feature names. The artifact is loaded from the path
specified by the caller, the LEXICAL_MODEL_PATH environment variable,
or the default repository-relative path.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .contracts import ClassifierPrediction, FeatureContribution, LocalExplanation


class LexicalClassifier:
    """Load a trained scikit-learn estimator and expose the classifier contract.

    The class wraps a trained multiclass classification model and provides
    methods for prediction, local feature contribution analysis, and metadata
    retrieval.

    The loaded model artifact is expected to contain:
        - "model": The trained scikit-learn estimator.
        - "feature_names": The ordered names of the features expected by the model.
        - "version" (optional): The version of the trained model artifact.

    Feature names are used to ensure that input values are supplied to the
    estimator in the same order used during training.
    """

    def __init__(self, model_path: str | Path | None = None):
        """Initialize the classifier from a persisted model artifact.

        The model is loaded from a joblib file. Once loaded, its parallel
        execution settings are adjusted for runtime inference, and the
        feature names, class labels, version, and feature importances
        are extracted from the artifact and estimator.

        :param model_path: Path to the joblib model artifact. If omitted,
            uses LEXICAL_MODEL_PATH or defaults to
            artifacts/lexical/model.joblib.
        :raises FileNotFoundError: If the model artifact does not exist.
        """

        # Resolve the model path using the following priority:
        # 1. An explicitly provided path.
        # 2. The LEXICAL_MODEL_PATH environment variable.
        # 3. The default artifact path.
        self.model_path = Path(model_path or os.getenv(
            "LEXICAL_MODEL_PATH", "artifacts/lexical/model.joblib"))

        # Verify that the model artifact exists before attempting to load it
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Lexical model not found at {self.model_path}. Train it first; see training/models/lexical/train.py"
            )

        # Deserialize the trained model artifact using joblib
        artifact = joblib.load(self.model_path)
        self.model = artifact["model"]

        # Configure the estimator for runtime inference
        # Disable parallel jobs and verbose output to avoid unnecessary
        # resource usage and logging during prediction requests
        self.model.set_params(n_jobs=1, verbose=0)

        # Store the ordered feature names from the training artifact
        self.feature_names = list(artifact["feature_names"])

        # Extract the class labels supported by the trained estimator
        self.classes = [str(value) for value in self.model.classes_]

        # Read the model artifact version
        # If no version is provided, use version 1 as the default
        self.version = str(artifact.get("version", 1))

        # Retrieve global feature importance values when the estimator exposes
        # feature_importances_
        self.feature_importances = getattr(self.model, "feature_importances_", None)

    def predict(self, features: Any) -> ClassifierPrediction:
        """Predict a class and its per-class probabilities.

        Converts the input features into a DataFrame with the expected column
        names and order, then obtains a probability for each trained class.
        The class with the highest predicted probability becomes the output
        label.

        :param features: Validated feature vector containing the values
            required by the trained model.
        :return: A multiclass prediction containing the predicted label
            and a mapping of class names to predicted probabilities.
        """

        # Convert the supplied features into a single-row DataFrame.
        row = self._row(features)

        # Obtain the predicted probability for each class
        probabilities = self.model.predict_proba(row)[0]

        # Identify the class with the highest predicted probability
        label = str(self.model.classes_[probabilities.argmax()])

        # Construct the standardized prediction result
        return ClassifierPrediction(
            kind="multiclass",
            label=label,
            scores={str(name): float(score) for name, score in zip(self.classes, probabilities)},
        )

    def explain(self, features: Any, prediction: ClassifierPrediction) -> LocalExplanation:
        """Generate an approximate local explanation for a prediction.

        This method estimates feature contributions by multiplying each
        feature's global importance by the absolute magnitude of its observed
        value. Features with the largest resulting weights are returned first.

        If the estimator does not expose global feature importances, uniform
        importance weights are used as a fallback.

        This is a lightweight diagnostic approximation, not a causal analysis
        or a SHAP explanation. The resulting contribution values are unsigned
        ranking scores and should not be interpreted as the direction or size
        of each feature's effect on the predicted probability.

        :param features: Validated feature vector used for the prediction.
        :param prediction: Prediction whose output should be explained.
        :return: A local explanation containing the target class, its output
            score when available, and the ten highest-ranked features.
        """

        # Convert the input features into the same ordered DataFrame format
        # used during prediction
        row = self._row(features)

        # Retrieve the model's global feature importances
        importances = self.feature_importances

        # If the estimator does not provide feature importances, assign equal
        # weights to all features so that the explanation can still be created
        if importances is None:
            importances = np.ones(len(self.feature_names), dtype=float) / len(self.feature_names)

        # Extract the feature values from the single input row as a numeric
        # NumPy array, preserving the order of self.feature_names
        values = row.iloc[0].to_numpy(dtype=float)

        # Calculate an unsigned ranking score for each feature
        # Multiplying global importance by absolute feature magnitude gives
        # greater weight to features that are both important to the model
        # overall and large in the current input
        #
        # These weights do not represent signed effects, causal relationships,
        # or SHAP values
        weights = np.asarray(importances, dtype=float) * np.abs(values)

        # Sort feature indices by descending ranking score and select
        # at most the ten highest-ranked features
        indices = np.argsort(weights)[::-1][:10]

        # Build a FeatureContribution object for each selected feature
        # Each entry includes the feature name, its original input value,
        # and its unsigned importance-weighted magnitude
        contributions = tuple(
            FeatureContribution(
                name=self.feature_names[index],
                value=float(values[index]),
                contribution=float(weights[index]),
            )
            for index in indices
        )

        # Retrieve the predicted score for the class being explained
        # If the prediction has no label, or its score mapping does not
        # contain that label, output_value will be None
        output = (prediction.scores or {}).get(prediction.label or "")

        # Return the explanation using the shared LocalExplanation contract
        return LocalExplanation(
            method="importance_weighted_magnitude",
            target=prediction.label,
            base_value=None,
            output_value=output,
            features=contributions,
        )

    def metadata(self) -> dict[str, Any]:
        """Return stable model metadata for service responses and logging.

        The metadata describes the classifier independently of any individual
        prediction. It includes the classifier name, the loaded model version,
        and the class labels supported by the trained estimator.

        :return: A dictionary containing the classifier name, model version,
            and available class labels.
        """

        return {"name": "lexical", "version": self.version, "classes": self.classes}

    def _row(self, features: Any) -> pd.DataFrame:
        """Convert an input feature vector into the model's expected format.

        The method accepts either an object exposing a ``values`` attribute
        or a mapping that can be converted into a dictionary. It then builds
        a single-row pandas DataFrame using the feature names and ordering
        recorded in the trained model artifact.

        This keeps prediction and explanation inputs consistent with the
        model's training-time feature layout.

        :param features: Feature vector or mapping containing the required
            feature values.
        :return: A single-row DataFrame with columns ordered according to
            self.feature_names.
        """

        # Extract the underlying feature mapping
        values = features.values if hasattr(features, "values") else dict(features)

        # Build a DataFrame containing one sample
        # Retrieve values in the exact order expected by the model, rather
        # than relying on the order in which the input mapping was created
        return pd.DataFrame([[values[name] for name in self.feature_names]], columns=self.feature_names)

# MLflow fallback

MLflow is retained as a fallback in case W&B is missing a required capability.

The conceptual mapping is:

| Requirement | Primary | Fallback |
|---|---|---|
| experiment tracking | W&B Runs | MLflow Tracking |
| dataset versioning | W&B Artifacts | lakeFS/MinIO or MLflow-linked artifact store |
| feature dataset lineage | W&B Artifacts | lakeFS/MinIO |
| model artifacts | W&B Artifacts/Registry | MLflow Model Registry |
| model metadata | W&B metadata | MLflow tags |
| tuning | W&B + Optuna | MLflow + Optuna |
| explainability artifacts | W&B Artifacts | MLflow Artifacts |

The application-level lineage contract must remain unchanged when switching tracking backends.

Do not couple feature extraction, classifiers or phase code directly to MLflow APIs.
Use a small tracking abstraction.

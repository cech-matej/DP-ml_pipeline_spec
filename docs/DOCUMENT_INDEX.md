# Documentation index

## Architecture
- `architecture.md` — standalone-first architecture and THOR integration boundary
- `phase.md` — phase = one microservice containing extractor(s) + classifier(s)
- `cascade.md` — phase/stage composition and orchestration responsibilities

## Data and features
- `datasets.md` — dataset-first versioning with W&B Artifacts
- `features.md` — single-source feature schema and executable validation
- `outliers.md` — model-specific outlier treatment

## Classifiers and inference
- `classifiers.md` — binary, multiclass and detector contracts
- `classifier-microservice.md` — standalone/HTTP/THOR service contract
- `inference.md` — inference result and per-feature explanations
- `explainability.md` — SHAP-first local explanations and global importance

## Training and testing
- `training-and-tuning.md` — training, tuning and model-centric evaluation
- `testing.md` — unit, schema, contract and integration tests
- `reproducibility.md` — W&B lineage and reproducible runs
- `contributing.md` — team workflow

## Tooling
- `adr-001-stack.md` — W&B-first stack decision
- `mlflow-fallback.md` — MLflow fallback mapping
- `wandb-metadata.md` — W&B metadata/artifact naming convention

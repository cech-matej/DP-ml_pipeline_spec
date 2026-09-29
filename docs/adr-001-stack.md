# ADR-001: W&B-first ML stack

Status: proposed.

## Decision

Use:

- Git for source code, feature schemas, classifier definitions, configs and docs;
- W&B for experiments, dataset/feature/model artifacts and model lifecycle;
- Python for extraction, training and inference;
- Docker for packaging phase microservices;
- optional Optuna for hyperparameter search.

MLflow is retained as a fallback integration.

## Why

W&B currently provides artifact-based data/model lineage and run tracking. Its academic offering advertises a free academic plan; the current pricing page states 200 GB cloud storage for academic use.

The ML application should remain independent of either tracking backend.

## Not included

- Kafka in the standalone ML pipeline;
- Redis/fact store;
- collectors;
- external API clients;
- THOR orchestration;
- online feature serving.

These are integration/runtime concerns outside the ML core.

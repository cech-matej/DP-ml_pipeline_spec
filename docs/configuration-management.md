# Configuration management

## One naming convention

Example files are marked by the `example_` prefix (or, for the cascade, `config/cascades/example.yaml`). Do not have production services automatically load these example files.

When you create real configurations, put versioned model/contract artifacts in a folder named after the artifact, then store immutable versions as `vN.yaml`. For example:

```text
config/
├── cascades/
│   ├── example.yaml
│   └── production.yaml          # illustrative path only; not committed here
├── classifiers/
│   ├── example_dom-phishing.yaml
│   ├── example_html-js.yaml
│   └── lexical/
│       ├── v1.yaml
│       └── v2.yaml
├── features/
│   ├── example_html-js.yaml
│   └── html-js/
│       └── v1.yaml
├── outliers/
│   ├── example_html-js.yaml
│   └── html-js-outliers/
│       └── v1.yaml
├── phases/
│   ├── example_html.yaml
│   └── html/
│       └── v1.yaml
├── deployments/
│   └── example-html-http.yaml
└── transports/
    └── example-html-http.yaml
```

Examples stay at the type directory level. Real versioned artifacts live in `<type>/<artifact>/vN.yaml`. Do not overwrite a published version: add a new version when the contract or behavior changes. Keep historical versions in Git for reproducibility. Cascades and deployment/transport wiring may use descriptive names rather than version directories when they represent environment-level configuration.

## Validation

Each configuration type has its own reusable schema in `schemas/config/`: cascade, classifier, deployment, feature, outliers, phase, and transport. The validation script discovers these schema files; field definitions are not hardcoded into Python. Update the matching schema when you add or change a config field.

```bash
pip install -e ".[dev]"
python scripts/validate_configs.py
python scripts/validate_configs.py config/classifiers/example_dom-phishing.yaml
python scripts/validate_configs.py config/classifiers/
```

The default command validates every YAML file under `config/`. Versioned files placed at paths such as `config/classifiers/lexical/v2.yaml` are checked against the relevant schema, including consistency between `v2` and the in-file version field.

## Training organization

All model training entry points and their reusable helper implementations live under `training/`: model-specific scripts are in `training/models/<model>/`, and shared helpers are in `training/shared/domain_detection_training/`. Each model has one entry point, reads its YAML settings, and imports shared helpers rather than duplicating them. Dataset identity/versioning must be recorded before feature extraction.

## Python package paths in `source_module`

The `src/` directory is a Python *source-layout* directory, not part of the import name. The package root is `src/domain_detection/`, so a module at:

```text
src/domain_detection/classifiers/dom_phishing.py
```

is imported as:

```yaml
implementation:
  source_module: domain_detection.classifiers.dom_phishing
```

Do not include `src.` in `source_module`. The `domain_detection/` directory is not a redundant extra level: it defines the importable Python package named `domain_detection`. This is also consistent with `[tool.setuptools.packages.find] where = ["src"]` in `pyproject.toml`.

A configured `source_module` must correspond to a real Python module before that classifier can be loaded. The example module names are illustrative until the corresponding classifier implementation files exist.

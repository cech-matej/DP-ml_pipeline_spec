# Model training workspace

All training code and its reusable helpers live under this directory.

```text
training/
├── models/
│   ├── html_js/train.py
│   └── dom_phishing/train.py
└── shared/
    ├── data.py
    ├── outliers.py
    └── train.py
```

Each model has one entry-point script under `models/<model>/train.py`. Shared dataset loading, training-only outlier filtering, and evaluation helpers live under `shared/`; model scripts should import these rather than copying the implementation. Model-specific settings are loaded from the relevant YAML files in `config/`.

Run a model entry point from the repository root, for example:

```bash
python training/models/html_js/train.py /path/to/versioned-dataset.parquet
python training/models/dom_phishing/train.py
```

The DOM phishing script is currently a configuration-loading placeholder until the reference-corpus/index-building workflow is specified.

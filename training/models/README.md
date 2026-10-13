# Model training jobs

Keep one directory per model family here. Each job is an entry point and should load its classifier, feature-schema and outlier-policy YAML rather than duplicating those settings in Python. Dataset paths/versions are supplied per run; canonical datasets must be versioned before feature extraction.

Examples:

- `html_js/train.py` uses the HTML/JS classifier and its configured outlier policy.
- `dom_phishing/train.py` uses the DOM similarity-detector config; its algorithm-specific training implementation is intentionally a placeholder until the detector's reference corpus/training contract is finalized.

Run the examples from the repository root after installing the project and its development dependencies.

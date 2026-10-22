from pathlib import Path

import yaml

from domain_detection.features.contracts import FeatureSchema
from domain_detection.features.lexical import LexicalExtractor


def test_batch_matches_single_domain_extraction(tmp_path: Path):
    config = yaml.safe_load(Path("config/features/lexical/v1.yaml").read_text())
    schema = FeatureSchema(config["schema"]["name"], config["schema"]["version"], config["features"])
    extractor = LexicalExtractor(schema, tmp_path)
    domains = ["www.example.com", "verify-account-login.test", "abc123.net"]
    batch = extractor.extract_batch(domains)
    single = [extractor.extract(domain).values for domain in domains]
    assert list(batch.columns) == [feature["name"] for feature in config["features"]]
    assert batch.to_dict(orient="records") == single

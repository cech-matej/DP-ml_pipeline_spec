import pandas as pd

from domain_detection.features.contracts import FeatureSchema
from domain_detection.features.lexical import LexicalExtractor


def test_only_configured_features_are_returned_and_parsed_lazily(monkeypatch, tmp_path):
    import domain_detection.features.lexical as lexical_module

    schema = FeatureSchema("lexical", 99, [{"name": "lex_name_len", "type": "int64", "nullable": False, "source": "domain_name"}])
    extractor = LexicalExtractor(schema, tmp_path)

    def fail_if_parsed(_domain):
        raise AssertionError("tldextract should not run when no configured feature needs parsed labels")

    monkeypatch.setattr(lexical_module.tldextract, "extract", fail_if_parsed)
    result = extractor.extract_batch(pd.Series(["example.com", "a.test"]))
    assert list(result.columns) == ["lex_name_len"]
    assert result["lex_name_len"].tolist() == [11, 6]

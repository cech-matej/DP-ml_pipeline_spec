from domain_detection.phases.runner import PhaseRunner
from domain_detection.phases.contracts import PhaseInput


class Extractor:
    def extract(self, source):
        return {"value": source["value"]}


class Classifier:
    version = "1"
    feature_schema = "demo"

    def predict(self, features):
        return {"label": "phishing" if features["value"] else "benign"}

    def explain(self, features, prediction):
        return {"method": "demo", "value": features["value"]}


def make_phase():
    return PhaseRunner(
        "html",
        "4",
        {"demo": Extractor()},
        {"demo-classifier": Classifier()},
        max_concurrent_domains=2,
    )


def test_batch_produces_result_for_each_domain():
    result = make_phase().run(PhaseInput(
        request_id="r1",
        domains=(
            {"domain_id": "a", "facts": {"demo": {"value": 1}}},
            {"domain_id": "b", "facts": {"demo": {"value": 0}}},
        ),
        include_explanations=False,
    ))
    assert [d.domain_id for d in result.domains] == ["a", "b"]
    assert all(c.explanation is None for d in result.domains for c in d.classifiers)


def test_explanations_are_only_computed_when_requested():
    result = make_phase().run(PhaseInput(
        request_id="r1",
        domains=({"domain_id": "a", "facts": {"demo": {"value": 1}}},),
        include_explanations=True,
    ))
    assert result.domains[0].classifiers[0].explanation["method"] == "demo"

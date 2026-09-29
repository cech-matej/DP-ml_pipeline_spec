from domain_detection.policies.rule_based import evaluate_rule_policy


def test_rule_policy_only_derives_phase_outcome():
    config = {"rules": [{"when_label": "phishing", "output": "phishing"}], "otherwise": "uncertain"}
    assert evaluate_rule_policy([{"prediction": {"label": "phishing"}}], config) == "phishing"
    assert evaluate_rule_policy([{"prediction": {"label": "benign"}}], config) == "uncertain"

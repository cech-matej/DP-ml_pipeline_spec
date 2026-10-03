from domain_detection.phases.contracts import ClassifierResult, DomainResult, PhaseResult
from domain_detection.serving.contracts import ServiceRequest, ServiceResponse, decode_json, encode_json


def test_request_round_trip_to_batch_phase_input():
    request = ServiceRequest.from_dict({
        "include_explanations": False,
        "domains": [
            {"domain_id": "example.com", "facts": {"html-js": {"body": "<html>"}}},
            {"domain_id": "example.org", "facts": {"html-js": {"body": "<html>"}}},
        ],
    })
    phase_input = request.to_phase_input()
    assert len(phase_input.domains) == 2
    assert phase_input.domains[0]["domain_id"] == "example.com"
    assert phase_input.include_explanations is False


def test_explanation_flag_round_trips():
    request = ServiceRequest.from_dict({
        "include_explanations": True,
        "domains": [{"domain_id": "example.com", "facts": {}}],
    })
    assert request.to_phase_input().include_explanations is True


def test_response_is_transport_serializable_and_batched():
    result = PhaseResult(
        phase="html",
        version="4",
        domains=(
            DomainResult(
                domain_id="example.com",
                classifiers=(
                    ClassifierResult(
                        classifier="demo",
                        version="1",
                        prediction={"kind": "classification", "label": "phishing"},
                        explanation=None,
                    ),
                ),
            ),
        ),
    )
    payload = ServiceResponse.from_phase_result(result).to_dict()
    encoded = decode_json(encode_json(payload))
    assert encoded["result"]["domains"][0]["domain_id"] == "example.com"
    assert "explanation" not in encoded["result"]["domains"][0]["classifiers"][0]


def test_request_does_not_accept_client_selected_phase_version():
    request = ServiceRequest.from_dict({
        "phase_version": "999",
        "domains": [{"domain_id": "example.com", "facts": {}}],
    })
    assert request.to_phase_input().domains[0]["domain_id"] == "example.com"


def test_duplicate_domain_ids_are_rejected():
    import pytest
    with pytest.raises(ValueError):
        ServiceRequest.from_dict({
            "domains": [
                {"domain_id": "example.com", "facts": {}},
                {"domain_id": "example.com", "facts": {}},
            ]
        })

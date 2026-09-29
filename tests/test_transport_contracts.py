from dataclasses import dataclass

from domain_detection.phases.contracts import ClassifierResult, PhaseResult
from domain_detection.serving.contracts import ServiceRequest, ServiceResponse, decode_json, encode_json


def test_request_round_trip_to_phase_input():
    request = ServiceRequest.from_dict({
        "request_id": "r1",
        "phase": "html",
        "phase_version": "4",
        "facts": {"html": {"body": "<html>"}},
    })
    assert request.to_phase_input().facts["html"]["body"] == "<html>"


def test_response_is_transport_serializable():
    result = PhaseResult(
        request_id="r1",
        phase="html",
        version="4",
        classifiers=(
            ClassifierResult(
                classifier="demo",
                version="1",
                prediction={"kind": "classification", "label": "phishing"},
                explanation={"method": "shap"},
            ),
        ),
    )
    payload = ServiceResponse.from_phase_result(result).to_dict()
    assert decode_json(encode_json(payload))["request_id"] == "r1"
    assert payload["result"]["classifiers"][0]["name"] == "demo"

from __future__ import annotations

from backend.errors import APIError, MODEL_UNAVAILABLE
from backend.services import complaint_service


def test_analyze_returns_contract_and_persists(client):
    response = client.post(
        "/api/complaints/analyze",
        json={"text": "I was charged twice for the same purchase."},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["complaint_id"] == 1
    assert body["intent"] == "card_arrival"
    assert body["confidence"] == 0.9137
    assert body["model"] == "tfidf"
    assert body["priority"] == "high"
    assert body["priority_reason"].startswith("Rule matched:")
    assert body["similar_cases"] == []
    assert body["summary"] is None
    assert body["summary_status"] == "unavailable"
    assert body["source"] == "submitted"
    assert body["created_at"].endswith("Z")

    listed = client.get("/api/complaints").json()
    assert listed["count"] == 1
    assert listed["items"][0]["complaint_id"] == 1


def test_second_submission_returns_similar_case(client):
    client.post("/api/complaints/analyze", json={"text": "My card has not arrived."})
    response = client.post(
        "/api/complaints/analyze", json={"text": "When will my card arrive?"}
    )
    assert response.status_code == 200
    cases = response.json()["similar_cases"]
    assert len(cases) == 1
    assert cases[0]["complaint_id"] == 1
    assert cases[0]["similarity"] == 0.9
    assert cases[0]["source"] == "submitted"


def test_blank_text_is_rejected(client):
    response = client.post("/api/complaints/analyze", json={"text": "   "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["field"] == "text"


def test_too_long_text_is_rejected(client):
    response = client.post("/api/complaints/analyze", json={"text": "x" * 2001})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_model_is_rejected(client):
    response = client.post(
        "/api/complaints/analyze", json={"text": "hello", "model": "nope"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNKNOWN_MODEL"
    assert response.json()["error"]["field"] == "model"


def test_missing_field_uses_error_envelope(client):
    response = client.post("/api/complaints/analyze", json={})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["field"] == "text"


def test_malformed_json_uses_error_envelope(client):
    response = client.post(
        "/api/complaints/analyze",
        content="{not valid json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_model_unavailable_is_503(client, monkeypatch):
    def unavailable():
        raise APIError(503, MODEL_UNAVAILABLE, "NLP components are not available yet.")

    monkeypatch.setattr(complaint_service, "_load_nlp", unavailable)
    response = client.post("/api/complaints/analyze", json={"text": "hello"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_UNAVAILABLE"


def test_unexpected_inference_failure_is_500(client_no_raise, monkeypatch):
    def explode():
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(complaint_service, "_load_nlp", explode)
    response = client_no_raise.post("/api/complaints/analyze", json={"text": "hello"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INFERENCE_ERROR"


def test_summary_enabled_is_returned(enabled_summary_client):
    response = enabled_summary_client.post(
        "/api/complaints/analyze", json={"text": "I was charged twice."}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "Customer reports an issue."
    assert body["summary_status"] == "enabled"

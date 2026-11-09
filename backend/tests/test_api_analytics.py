from __future__ import annotations

from backend.db import repository


def test_analytics_empty_database(client):
    response = client.get("/api/analytics")
    assert response.status_code == 200
    assert response.json() == {
        "total_complaints": 0,
        "by_intent": [],
        "by_priority": [],
        "most_common_intents": [],
        "includes_demo": False,
    }


def test_analytics_reflects_submissions(client):
    client.post("/api/complaints/analyze", json={"text": "First complaint about my card."})
    client.post("/api/complaints/analyze", json={"text": "Second complaint about my card."})

    body = client.get("/api/analytics").json()
    assert body["total_complaints"] == 2
    assert body["by_intent"] == [{"intent": "card_arrival", "count": 2}]
    assert body["by_priority"] == [{"priority": "high", "count": 2}]
    assert body["most_common_intents"] == [{"intent": "card_arrival", "count": 2}]
    assert body["includes_demo"] is False


def test_health_reports_models_and_database(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["models"] == {"tfidf": True, "sbert": False}
    assert body["summary"] == "unavailable"
    assert body["database"] == "ok"


def test_unknown_route_uses_error_envelope(client):
    response = client.get("/api/unknown")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_list_pagination_is_validated(client):
    response = client.get("/api/complaints?limit=0")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    response = client.get("/api/complaints?limit=101")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_demo_rows_are_flagged(client):
    repository.insert_complaint(
        text="Demo complaint about a card.",
        normalized_text="Demo complaint about a card.",
        intent="card_arrival",
        confidence=0.0,
        model="demo-seed",
        priority="low",
        priority_reason="Rule matched: informational request",
        summary=None,
        summary_status="unavailable",
        source="demo",
        created_at="2026-11-09T10:00:00Z",
    )

    analytics = client.get("/api/analytics").json()
    assert analytics["includes_demo"] is True
    assert analytics["total_complaints"] == 1

    items = client.get("/api/complaints").json()["items"]
    assert items[0]["source"] == "demo"


def test_list_supports_pagination(client):
    client.post("/api/complaints/analyze", json={"text": "First complaint."})
    client.post("/api/complaints/analyze", json={"text": "Second complaint."})

    first_page = client.get("/api/complaints?limit=1&offset=0").json()
    second_page = client.get("/api/complaints?limit=1&offset=1").json()

    assert first_page["count"] == 1
    assert second_page["count"] == 1
    assert first_page["items"][0]["complaint_id"] != second_page["items"][0]["complaint_id"]

from __future__ import annotations


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

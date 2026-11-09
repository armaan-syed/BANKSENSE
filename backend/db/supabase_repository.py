"""Data access via the Supabase Data API (PostgREST).

The access token used here is always a signed Supabase Auth access token. That
means Row Level Security inside Supabase — rather than the API layer — is what
limits a request to the signed-in user's records.
"""

from __future__ import annotations

from typing import Any

import httpx

from backend.config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL


def _rest_url() -> str:
    return f"{SUPABASE_URL.rstrip('/')}/rest/v1"


def _headers(access_token: str | None) -> dict[str, str]:
    return {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {access_token or SUPABASE_PUBLISHABLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _client() -> httpx.Client:
    return httpx.Client(timeout=10.0)


def _select(query: dict[str, Any], access_token: str | None) -> list[dict[str, Any]]:
    with _client() as client:
        response = client.get(f"{_rest_url()}/complaints", params=query, headers=_headers(access_token))
        response.raise_for_status()
        return response.json()


def insert_complaint(
    *,
    user_id: str,
    text: str,
    normalized_text: str,
    intent: str,
    confidence: float,
    model: str,
    priority: str,
    priority_reason: str,
    summary: str | None,
    summary_status: str,
    source: str,
    created_at: str,
    access_token: str,
) -> int | str:
    payload = {
        "user_id": user_id,
        "text": text,
        "normalized_text": normalized_text,
        "intent": intent,
        "confidence": confidence,
        "model": model,
        "priority": priority,
        "priority_reason": priority_reason,
        "summary": summary,
        "summary_status": summary_status,
        "source": source,
        "created_at": created_at,
    }
    headers = _headers(access_token)
    headers["Prefer"] = "return=representation"
    with _client() as client:
        response = client.post(f"{_rest_url()}/complaints", json=payload, headers=headers)
        response.raise_for_status()
        rows = response.json()
        if not rows:
            raise RuntimeError("Supabase INSERT returned no data.")
        return rows[0]["id"]


def fetch_recent(
    limit: int,
    offset: int,
    access_token: str | None,
) -> list[dict[str, Any]]:
    return _select(
        {
            "select": "id,text,intent,confidence,model,priority,priority_reason,"
            "summary,summary_status,source,created_at",
            "order": "created_at.desc,id.desc",
            "limit": limit,
            "offset": offset,
        },
        access_token,
    )


def fetch_candidates(access_token: str | None) -> list[dict[str, Any]]:
    return _select(
        {"select": "id,text,intent,source", "order": "id.desc", "limit": 1000},
        access_token,
    )


def is_allowed_user(email: str | None, access_token: str) -> bool:
    if not email:
        return False
    with _client() as client:
        response = client.get(
            f"{_rest_url()}/allowed_users",
            params={"select": "email", "email": f"eq.{email.lower()}", "limit": 1},
            headers=_headers(access_token),
        )
        response.raise_for_status()
        return bool(response.json())


def analytics(access_token: str | None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = _select(
            {
                "select": "intent,priority,source",
                "order": "id.desc",
                "limit": 1000,
                "offset": offset,
            },
            access_token,
        )
        rows.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
        if offset >= 50000:
            break

    by_intent: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    includes_demo = False
    for row in rows:
        intent = str(row.get("intent") or "unknown")
        priority = str(row.get("priority") or "low")
        by_priority[priority] = by_priority.get(priority, 0) + 1
        by_intent[intent] = by_intent.get(intent, 0) + 1
        if row.get("source") == "demo":
            includes_demo = True

    by_intent_sorted = sorted(by_intent.items(), key=lambda item: (-item[1], item[0]))
    by_priority_sorted = sorted(by_priority.items(), key=lambda item: (-item[1], item[0]))
    return {
        "total_complaints": len(rows),
        "by_intent": [{"intent": key, "count": value} for key, value in by_intent_sorted],
        "by_priority": [{"priority": key, "count": value} for key, value in by_priority_sorted],
        "most_common_intents": [
            {"intent": key, "count": value} for key, value in by_intent_sorted[:5]
        ],
        "includes_demo": includes_demo,
    }


def check_database(access_token: str | None = None) -> str:
    """Verify the Supabase REST endpoint is reachable and configured."""
    if not SUPABASE_URL:
        return "error"

    headers = _headers(access_token)
    headers.pop("Authorization", None)
    try:
        with _client() as client:
            response = client.get(
                f"{SUPABASE_URL.rstrip('/')}/auth/v1/health",
                headers=headers,
            )
            response.raise_for_status()
    except Exception:
        return "error"
    return "ok"

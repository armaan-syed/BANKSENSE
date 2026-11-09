from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from backend import config
from backend.db import sqlite_repository, supabase_repository


def is_supabase() -> bool:
    return config.DATABASE_BACKEND == "supabase"


def insert_complaint(
    *,
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
    path: Path | None = None,
    user_id: str | None = None,
    access_token: str | None = None,
) -> int | str:
    if is_supabase():
        if not user_id or not access_token:
            raise ValueError("Supabase inserts require a user and access token.")
        return supabase_repository.insert_complaint(
            user_id=user_id,
            text=text,
            normalized_text=normalized_text,
            intent=intent,
            confidence=confidence,
            model=model,
            priority=priority,
            priority_reason=priority_reason,
            summary=summary,
            summary_status=summary_status,
            source=source,
            created_at=created_at,
            access_token=access_token,
        )
    return sqlite_repository.insert_complaint(
        text=text,
        normalized_text=normalized_text,
        intent=intent,
        confidence=confidence,
        model=model,
        priority=priority,
        priority_reason=priority_reason,
        summary=summary,
        summary_status=summary_status,
        source=source,
        created_at=created_at,
        path=path,
    )


def fetch_recent(
    limit: int,
    offset: int,
    path: Path | None = None,
    access_token: str | None = None,
) -> list[sqlite3.Row] | list[dict[str, Any]]:
    if is_supabase():
        return supabase_repository.fetch_recent(limit, offset, access_token)
    return sqlite_repository.fetch_recent(limit=limit, offset=offset, path=path)


def fetch_candidates(
    path: Path | None = None,
    access_token: str | None = None,
) -> list[dict[str, Any]]:
    if is_supabase():
        return supabase_repository.fetch_candidates(access_token)
    return sqlite_repository.fetch_candidates(path=path)


def analytics(
    path: Path | None = None,
    access_token: str | None = None,
) -> dict[str, Any]:
    if is_supabase():
        return supabase_repository.analytics(access_token)
    return sqlite_repository.analytics(path=path)


def is_allowed_user(email: str | None, access_token: str) -> bool:
    if is_supabase():
        return supabase_repository.is_allowed_user(email, access_token)
    return True


def check_database(access_token: str | None = None) -> str:
    if is_supabase():
        return supabase_repository.check_database(access_token)
    from backend.db.connection import check_database as sqlite_check

    return sqlite_check()

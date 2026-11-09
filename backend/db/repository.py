from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.db.connection import session


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
) -> int:
    with session(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO complaints (
                text, normalized_text, intent, confidence, model,
                priority, priority_reason, summary, summary_status, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                text,
                normalized_text,
                intent,
                confidence,
                model,
                priority,
                priority_reason,
                summary,
                summary_status,
                source,
                created_at,
            ),
        )
        return int(cursor.lastrowid)


def fetch_recent(
    limit: int,
    offset: int,
    path: Path | None = None,
) -> list[sqlite3.Row]:
    with session(path) as connection:
        rows = connection.execute(
            """
            SELECT id, text, intent, confidence, model, priority, priority_reason,
                   summary, summary_status, source, created_at
            FROM complaints
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return list(rows)


def fetch_candidates(path: Path | None = None) -> list[dict]:
    with session(path) as connection:
        rows = connection.execute(
            "SELECT id, text, intent, source FROM complaints ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def analytics(path: Path | None = None) -> dict:
    with session(path) as connection:
        total = connection.execute("SELECT COUNT(*) AS count FROM complaints").fetchone()[
            "count"
        ]
        by_intent = [
            dict(row)
            for row in connection.execute(
                """
                SELECT intent, COUNT(*) AS count
                FROM complaints
                GROUP BY intent
                ORDER BY count DESC, intent ASC
                """
            ).fetchall()
        ]
        by_priority = [
            dict(row)
            for row in connection.execute(
                """
                SELECT priority, COUNT(*) AS count
                FROM complaints
                GROUP BY priority
                ORDER BY count DESC, priority ASC
                """
            ).fetchall()
        ]
        includes_demo = bool(
            connection.execute(
                "SELECT EXISTS(SELECT 1 FROM complaints WHERE source = 'demo') AS present"
            ).fetchone()["present"]
        )
    return {
        "total_complaints": total,
        "by_intent": by_intent,
        "by_priority": by_priority,
        "most_common_intents": by_intent[:5],
        "includes_demo": includes_demo,
    }

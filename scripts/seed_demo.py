#!/usr/bin/env python3
"""Insert clearly labelled demo complaints for dashboard/similarity demos.

These rows are hand-authored demonstration data, not model predictions and not
real bank complaint history. They are stored with source="demo" so the API,
dashboard, and similar-case list can distinguish them from user submissions.

Usage:
    python -m scripts.seed_demo
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.db import repository
from backend.db.connection import init_db

DEMO_ROWS = [
    {
        "text": "I was charged twice for the same card purchase.",
        "intent": "transaction_charged_twice",
        "priority": "high",
        "priority_reason": "Rule matched: duplicate or repeated charge",
    },
    {
        "text": "My card was used for a payment I did not authorise.",
        "intent": "card_payment_not_recognised",
        "priority": "critical",
        "priority_reason": "Rule matched: unauthorised card activity",
    },
    {
        "text": "The cash machine did not dispense the money but my balance changed.",
        "intent": "cash_withdrawal_not_recognised",
        "priority": "medium",
        "priority_reason": "Rule matched: cash withdrawal access issue",
    },
    {
        "text": "How long does a refund to my card usually take?",
        "intent": "refund_not_showing_up",
        "priority": "medium",
        "priority_reason": "Rule matched: refund status enquiry",
    },
    {
        "text": "What is the exchange rate for a payment in euros?",
        "intent": "exchange_rate",
        "priority": "low",
        "priority_reason": "Rule matched: informational request",
    },
]


def main() -> int:
    if repository.is_supabase():
        print(
            "seed_demo targets the local SQLite database. "
            "Set BANKSENSE_DB_BACKEND=sqlite to seed demo rows."
        )
        return 1

    init_db()
    existing = repository.fetch_candidates()
    if any(candidate["source"] == "demo" for candidate in existing):
        print("demo rows already present; nothing to do")
        return 0

    now = datetime.now(timezone.utc).replace(microsecond=0)
    for offset, row in enumerate(DEMO_ROWS):
        created_at = (now - timedelta(minutes=offset)).isoformat().replace("+00:00", "Z")
        repository.insert_complaint(
            text=row["text"],
            normalized_text=" ".join(row["text"].split()),
            intent=row["intent"],
            confidence=0.0,
            model="demo-seed",
            priority=row["priority"],
            priority_reason=row["priority_reason"],
            summary=None,
            summary_status="unavailable",
            source="demo",
            created_at=created_at,
        )
    print(f"inserted {len(DEMO_ROWS)} demo complaints (source='demo')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.db import connection
from backend.services import complaint_service


class FakePredictor:
    class InvalidInputError(Exception):
        pass

    class UnknownModelError(Exception):
        pass

    class ArtifactUnavailableError(Exception):
        pass

    @staticmethod
    def predict(text: str, model: str = "tfidf") -> dict:
        return {"intent": "card_arrival", "confidence": 0.9137, "model": model}

    @staticmethod
    def health() -> dict:
        return {"tfidf": True, "sbert": False, "summary": "unavailable"}


class FakePriority:
    @staticmethod
    def suggest_priority(text: str, intent: str) -> dict:
        return {
            "priority": "high",
            "priority_reason": "Rule matched: duplicate or repeated charge",
            "rule_id": "duplicate_charge",
        }


class FakeSimilarity:
    @staticmethod
    def rank_similar(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        return [dict(candidate, similarity=0.9) for candidate in candidates[:top_k]]


class FakeSummarizer:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def summary_status(self) -> str:
        return "enabled" if self.enabled else "unavailable"

    def summarize(self, text: str, max_len: int = 60) -> dict:
        if not self.enabled:
            return {
                "status": "unavailable",
                "summary": None,
                "summary_status": "unavailable",
                "reason": "disabled in tests",
            }
        return {
            "status": "ok",
            "summary": "Customer reports an issue.",
            "summary_status": "enabled",
        }


def make_nlp(summarizer_enabled: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        predictor=FakePredictor,
        priority=FakePriority,
        similarity=FakeSimilarity,
        summarizer=FakeSummarizer(enabled=summarizer_enabled),
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(connection, "DATABASE_PATH", db_path)
    monkeypatch.setattr(complaint_service, "_load_nlp", lambda: make_nlp())

    from backend.app import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_no_raise(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(connection, "DATABASE_PATH", db_path)
    monkeypatch.setattr(complaint_service, "_load_nlp", lambda: make_nlp())

    from backend.app import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def enabled_summary_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(connection, "DATABASE_PATH", db_path)
    monkeypatch.setattr(
        complaint_service, "_load_nlp", lambda: make_nlp(summarizer_enabled=True)
    )

    from backend.app import app

    with TestClient(app) as test_client:
        yield test_client

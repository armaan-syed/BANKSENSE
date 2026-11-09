"""Shared constants for BankSense.

This module is the single source of truth for validation limits and the
priority scale used by both the NLP layer and the API layer. Person B imports
these instead of redefining them so request validation cannot drift.
"""

import os
from pathlib import Path

MAX_TEXT_LENGTH = 2000
SUPPORTED_MODELS = ("tfidf", "sbert")
DEFAULT_MODEL = "tfidf"
PRIORITIES = ("low", "medium", "high", "critical")

_BACKEND_DIR = Path(__file__).resolve().parents[1]


def _resolve_dir(env_name: str, default: Path) -> Path:
    value = os.environ.get(env_name)
    return Path(value).expanduser().resolve() if value else default


MODELS_DIR = _resolve_dir("BANKSENSE_MODELS_DIR", _BACKEND_DIR / "models")
REPORTS_DIR = _resolve_dir("BANKSENSE_REPORTS_DIR", _BACKEND_DIR / "reports")

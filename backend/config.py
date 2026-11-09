import os
from pathlib import Path

from backend.nlp.config import (
    DEFAULT_MODEL,
    MAX_TEXT_LENGTH,
    PRIORITIES,
    SUPPORTED_MODELS,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _database_path() -> Path:
    value = os.environ.get("BANKSENSE_DB_PATH")
    return Path(value).expanduser().resolve() if value else REPO_ROOT / "data" / "banksense.db"


def _cors_origins() -> list[str]:
    value = os.environ.get(
        "BANKSENSE_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in value.split(",") if origin.strip()]


DATABASE_PATH = _database_path()
CORS_ORIGINS = _cors_origins()
DEFAULT_LIST_LIMIT = 20
MAX_LIST_LIMIT = 100
SIMILAR_CASES_TOP_K = 5

__all__ = [
    "CORS_ORIGINS",
    "DATABASE_PATH",
    "DEFAULT_LIST_LIMIT",
    "DEFAULT_MODEL",
    "MAX_LIST_LIMIT",
    "MAX_TEXT_LENGTH",
    "PRIORITIES",
    "SIMILAR_CASES_TOP_K",
    "SUPPORTED_MODELS",
]

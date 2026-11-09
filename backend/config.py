import os
from pathlib import Path

from backend.env import load_runtime_env

load_runtime_env()

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
    value = os.environ.get("BANKSENSE_CORS_ORIGINS")
    if not value:
        value = "http://localhost:5173,http://127.0.0.1:5173"
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def _env_value(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


DATABASE_PATH = _database_path()
CORS_ORIGINS = _cors_origins()
DEFAULT_LIST_LIMIT = 20
MAX_LIST_LIMIT = 100
SIMILAR_CASES_TOP_K = 5

# Database backend selection. `sqlite` is local/dev; `supabase` is production.
# When unset, use Supabase if its connection settings are present.
DATABASE_BACKEND = _env_value("BANKSENSE_DB_BACKEND").lower()

SUPABASE_URL = _env_value("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = _env_value("SUPABASE_PUBLISHABLE_KEY") or _env_value(
    "SUPABASE_ANON_KEY"
)
SUPABASE_SECRET_KEY = _env_value("SUPABASE_SECRET_KEY")
SUPABASE_JWT_SECRET = _env_value("SUPABASE_JWT_SECRET")
SUPABASE_JWKS_URL = _env_value(
    "SUPABASE_JWKS_URL"
) or f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"

if not DATABASE_BACKEND:
    DATABASE_BACKEND = "supabase" if SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY else "sqlite"

__all__ = [
    "CORS_ORIGINS",
    "DATABASE_BACKEND",
    "DATABASE_PATH",
    "DEFAULT_LIST_LIMIT",
    "DEFAULT_MODEL",
    "MAX_LIST_LIMIT",
    "MAX_TEXT_LENGTH",
    "PRIORITIES",
    "SIMILAR_CASES_TOP_K",
    "SUPPORTED_MODELS",
    "SUPABASE_JWKS_URL",
    "SUPABASE_JWT_SECRET",
    "SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_SECRET_KEY",
    "SUPABASE_URL",
]

from __future__ import annotations

from pathlib import Path

_loaded = False


def load_runtime_env() -> None:
    """Load the root .env file once before backend settings are read."""
    global _loaded
    if _loaded:
        return
    try:
        from dotenv import load_dotenv

        repo_root = Path(__file__).resolve().parents[1]
        load_dotenv(repo_root / ".env", override=False)
    except Exception:
        # Environment loading should never prevent the API from starting.
        pass
    _loaded = True

"""Shared constants for BankSense.

This module is the single source of truth for validation limits and the
priority scale used by both the NLP layer and the API layer. Person B imports
these instead of redefining them so request validation cannot drift.
"""

import os
import re
from pathlib import Path

MAX_TEXT_LENGTH = 2000
SUPPORTED_MODELS = ("tfidf", "sbert")
DEFAULT_MODEL = "tfidf"
PRIORITIES = ("low", "medium", "high", "critical")

DEFAULT_TEXT_FIELD = "normalized_text"
EXPECTED_LABEL_COUNT = 77
RANDOM_SEED = 42
VALIDATION_SIZE = 0.1

TFIDF_ARTIFACT_NAME = "tfidf_logreg.joblib"
SBERT_ARTIFACT_NAME = "sbert_logreg.joblib"
LABEL_CLASSES_NAME = "label_classes.json"
SBERT_MODEL_NAME_FILE = "sbert_model_name.txt"
TRAINING_METADATA_NAME = "training_metadata.json"

_BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = _BACKEND_DIR.parent


def _resolve_dir(env_name: str, default: Path) -> Path:
    value = os.environ.get(env_name)
    return Path(value).expanduser().resolve() if value else default


MODELS_DIR = _resolve_dir("BANKSENSE_MODELS_DIR", _BACKEND_DIR / "models")
REPORTS_DIR = _resolve_dir("BANKSENSE_REPORTS_DIR", _BACKEND_DIR / "reports")

DEFAULT_SBERT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_SBERT_MODEL_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")


def validate_sbert_model_name(value: str, source: str = "SBERT model name") -> str:
    """Validate a Hugging Face model identifier without silently changing it.

    The artifact file is authoritative in production. If it is missing or
    malformed, callers must fail rather than substitute a different encoder.
    """

    if not isinstance(value, str):
        raise ValueError(f"{source} must be a string")
    name = value.strip()
    if not name:
        raise ValueError(f"{source} is empty")
    if any(character.isspace() for character in name):
        raise ValueError(
            f"{source} must contain a single model identifier without whitespace: "
            f"{value!r}"
        )
    if not _SBERT_MODEL_NAME_RE.fullmatch(name):
        raise ValueError(
            f"{source} is not a valid Hugging Face model identifier: {name!r}"
        )
    if any(part in {"", ".", ".."} for part in name.split("/")):
        raise ValueError(f"{source} contains an invalid path segment: {name!r}")
    return name


def _load_sbert_model_name() -> str:
    """Resolve the encoder name, preferring the trained artifact's record.

    - Production/Docker: `sbert_model_name.txt` is present and authoritative.
    - Local training: no artifact file yet, so `BANKSENSE_SBERT_MODEL` (or the
      default) selects the encoder that will be written to the file.
    """

    path = MODELS_DIR / SBERT_MODEL_NAME_FILE
    if path.is_file():
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Unable to read SBERT model name artifact {path}: {exc}") from exc
        try:
            return validate_sbert_model_name(raw, str(path))
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid SBERT model name artifact {path}: {exc}"
            ) from exc

    override = os.environ.get("BANKSENSE_SBERT_MODEL", "")
    if override.strip():
        try:
            return validate_sbert_model_name(override, "BANKSENSE_SBERT_MODEL")
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
    return DEFAULT_SBERT_MODEL_NAME


SBERT_MODEL_NAME = _load_sbert_model_name()
SUMMARY_MODEL_NAME = os.environ.get(
    "BANKSENSE_SUMMARY_MODEL", "sshleifer/distilbart-cnn-12-6"
)


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", ""}


# The optional summariser downloads a ~1.2 GB model on first use. Keep it
# enabled for local development, but set BANKSENSE_ENABLE_SUMMARY=0 on small
# hosts. backend/fly.toml sets it to 0 for the 2 GB Fly.io machine.
SUMMARY_ENABLED = _env_flag("BANKSENSE_ENABLE_SUMMARY", True)

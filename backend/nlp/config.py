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

DEFAULT_TEXT_FIELD = "normalized_text"
EXPECTED_LABEL_COUNT = 77
RANDOM_SEED = 42
VALIDATION_SIZE = 0.1

SBERT_MODEL_NAME = os.environ.get(
    "BANKSENSE_SBERT_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
SUMMARY_MODEL_NAME = os.environ.get(
    "BANKSENSE_SUMMARY_MODEL", "sshleifer/distilbart-cnn-12-6"
)

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

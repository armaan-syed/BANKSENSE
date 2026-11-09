"""Load and validate Person B's processed BANKING77 splits.

This module never edits the CSVs. It only reports what it finds so that
training uses exactly the data described in `data/processed/dataset_manifest.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.nlp.config import DEFAULT_TEXT_FIELD, EXPECTED_LABEL_COUNT, REPO_ROOT

PROCESSED_DIR = REPO_ROOT / "data" / "processed"
RAW_DIR = REPO_ROOT / "data" / "raw"
TRAIN_PATH = PROCESSED_DIR / "train.csv"
TEST_PATH = PROCESSED_DIR / "test.csv"
CATEGORIES_CANDIDATES = (
    PROCESSED_DIR / "categories.json",
    RAW_DIR / "categories.json",
)
REQUIRED_COLUMNS = ["example_id", "text", "normalized_text", "label"]


class DatasetError(Exception):
    """Raised when the processed dataset violates the shared contract."""


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise DatasetError(f"Dataset file not found: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(frame.columns) != REQUIRED_COLUMNS:
        raise DatasetError(
            f"{path.name} has columns {list(frame.columns)}, expected {REQUIRED_COLUMNS}"
        )
    return frame


def _normalize(text: str) -> str:
    return " ".join(str(text).split())


def _validate_split(frame: pd.DataFrame, name: str) -> list[str]:
    if list(frame.columns) != REQUIRED_COLUMNS:
        raise DatasetError(
            f"{name} has columns {list(frame.columns)}, expected {REQUIRED_COLUMNS}"
        )
    issues: list[str] = []
    if frame["example_id"].duplicated().any():
        issues.append(f"{name}: duplicate example_id values")
    if not frame["example_id"].str.startswith(name).all():
        issues.append(f"{name}: example_id prefix mismatch")
    for column in ("text", "normalized_text", "label"):
        empty = (frame[column].str.strip() == "").sum()
        if empty:
            issues.append(f"{name}: {empty} empty {column} values")
    return issues


def load_train() -> pd.DataFrame:
    return _read_csv(TRAIN_PATH)


def load_test() -> pd.DataFrame:
    return _read_csv(TEST_PATH)


def load_categories() -> list[str] | None:
    """Return categories.json when present (raw or processed), else None."""
    for path in CATEGORIES_CANDIDATES:
        if not path.exists():
            continue
        labels = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(labels, list) or not all(
            isinstance(label, str) for label in labels
        ):
            raise DatasetError(f"{path} must be a JSON list of label strings")
        return labels
    return None


def validate_dataset(
    train: pd.DataFrame | None = None,
    test: pd.DataFrame | None = None,
    text_field: str = DEFAULT_TEXT_FIELD,
) -> dict:
    """Validate both splits against the contract and return a JSON-safe report."""

    train = load_train() if train is None else train
    test = load_test() if test is None else test
    categories = load_categories()

    issues = _validate_split(train, "train") + _validate_split(test, "test")

    train_labels = set(train["label"])
    test_labels = set(test["label"])
    observed = train_labels | test_labels
    if len(observed) != EXPECTED_LABEL_COUNT:
        issues.append(
            f"observed {len(observed)} labels, expected {EXPECTED_LABEL_COUNT}"
        )
    if train_labels != test_labels:
        issues.append(
            "train/test label sets differ "
            f"(train only={sorted(train_labels - test_labels)}, "
            f"test only={sorted(test_labels - train_labels)})"
        )
    if categories is not None:
        expected = set(categories)
        if expected != observed:
            issues.append(
                "categories.json does not match the split labels "
                f"(missing={sorted(expected - observed)}, "
                f"unexpected={sorted(observed - expected)})"
            )

    normalized_mismatch = int(
        (train["normalized_text"] != train["text"].map(_normalize)).sum()
        + (test["normalized_text"] != test["text"].map(_normalize)).sum()
    )
    if normalized_mismatch:
        issues.append(
            f"{normalized_mismatch} normalized_text values differ from whitespace-normalized text"
        )

    report = {
        "text_field": text_field,
        "split_sizes": {"train": len(train), "test": len(test)},
        "label_count": len(observed),
        "labels": sorted(observed),
        "train_label_count": len(train_labels),
        "test_label_count": len(test_labels),
        "label_parity": train_labels == test_labels,
        "duplicate_texts": {
            "train": int(train["text"].duplicated().sum()),
            "test": int(test["text"].duplicated().sum()),
        },
        "empty_values": {
            column: {
                "train": int((train[column].str.strip() == "").sum()),
                "test": int((test[column].str.strip() == "").sum()),
            }
            for column in ("text", "normalized_text", "label")
        },
        "normalized_text_mismatches": int(normalized_mismatch),
        "per_label_train": {
            str(key): int(value)
            for key, value in train["label"].value_counts().sort_index().items()
        },
        "per_label_test": {
            str(key): int(value)
            for key, value in test["label"].value_counts().sort_index().items()
        },
        "issues": issues,
        "valid": not issues,
    }
    return report


def ensure_valid_dataset() -> dict:
    report = validate_dataset()
    if not report["valid"]:
        raise DatasetError("; ".join(report["issues"]))
    return report

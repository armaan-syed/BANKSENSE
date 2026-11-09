"""Deterministic, model-agnostic text preparation.

Person B already produced `normalized_text` (trim + collapse whitespace). We
use that column for both models so a single text field is evaluated everywhere.
"""

from __future__ import annotations

import pandas as pd

from backend.nlp.config import DEFAULT_TEXT_FIELD


def clean_text(text: str) -> str:
    return " ".join(str(text).split())


def texts_from_frame(frame: pd.DataFrame, field: str = DEFAULT_TEXT_FIELD) -> list[str]:
    if field not in frame.columns:
        raise ValueError(f"Text field '{field}' is not present in the dataset")
    return [clean_text(value) for value in frame[field].tolist()]

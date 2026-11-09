"""Process-wide cached Sentence-BERT encoder.

The encoder is shared by the SBERT classifier and the similarity search so a
single model instance is loaded per process. Embeddings are L2-normalised,
which makes the dot product equal to cosine similarity.
"""

from __future__ import annotations

import threading

import numpy as np

from backend.nlp.config import SBERT_MODEL_NAME
from backend.nlp.errors import ArtifactUnavailableError

_encoder = None
_lock = threading.Lock()


def get_encoder():
    global _encoder
    if _encoder is not None:
        return _encoder
    with _lock:
        if _encoder is not None:
            return _encoder
        try:
            from sentence_transformers import SentenceTransformer

            _encoder = SentenceTransformer(SBERT_MODEL_NAME)
        except Exception as exc:  # pragma: no cover - depends on local install
            raise ArtifactUnavailableError(
                f"Sentence-BERT model '{SBERT_MODEL_NAME}' is unavailable: {exc}"
            ) from exc
    return _encoder


def reset_encoder() -> None:
    global _encoder
    with _lock:
        _encoder = None


def encode_texts(texts: list[str], batch_size: int = 64) -> np.ndarray:
    if not texts:
        return np.empty((0, 384), dtype=np.float32)
    model = get_encoder()
    try:
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
    except Exception as exc:  # pragma: no cover - depends on local install
        raise ArtifactUnavailableError(f"Sentence-BERT encoding failed: {exc}") from exc
    return np.asarray(vectors, dtype=np.float32)


def encode_one(text: str) -> np.ndarray:
    return encode_texts([text])[0]

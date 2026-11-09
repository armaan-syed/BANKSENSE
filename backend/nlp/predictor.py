"""Stable inference interface used by the FastAPI service.

Models and the SBERT encoder are loaded once per process and cached. All
return values are plain Python types so the API layer never touches sklearn
or sentence-transformers objects.
"""

from __future__ import annotations

import json
import threading

import numpy as np

from backend.nlp.config import (
    DEFAULT_MODEL,
    LABEL_CLASSES_NAME,
    MAX_TEXT_LENGTH,
    MODELS_DIR,
    SBERT_ARTIFACT_NAME,
    SBERT_MODEL_NAME,
    SUPPORTED_MODELS,
    TFIDF_ARTIFACT_NAME,
)
from backend.nlp.encoder import encode_one
from backend.nlp.errors import (
    ArtifactUnavailableError,
    InvalidInputError,
    NLPError,
    UnknownModelError,
)

__all__ = [
    "SUPPORTED_MODELS",
    "NLPError",
    "InvalidInputError",
    "UnknownModelError",
    "ArtifactUnavailableError",
    "predict",
    "predict_top_k",
    "health",
]

_models: dict[str, object] = {}
_labels: list[str] | None = None
_lock = threading.Lock()


def _artifact_path(model_name: str):
    filename = TFIDF_ARTIFACT_NAME if model_name == "tfidf" else SBERT_ARTIFACT_NAME
    return MODELS_DIR / filename


def _load_label_classes() -> list[str]:
    global _labels
    if _labels is not None:
        return _labels
    path = MODELS_DIR / LABEL_CLASSES_NAME
    try:
        labels = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ArtifactUnavailableError(
            f"Label classes artifact is unavailable at {path}: {exc}"
        ) from exc
    if not isinstance(labels, list) or not labels:
        raise ArtifactUnavailableError(f"Invalid label classes artifact at {path}")
    _labels = [str(label) for label in labels]
    return _labels


def _load_model(model_name: str):
    if model_name not in SUPPORTED_MODELS:
        raise UnknownModelError(
            f"Unsupported model '{model_name}'. Choose one of: {', '.join(SUPPORTED_MODELS)}"
        )
    if model_name in _models:
        return _models[model_name]

    with _lock:
        if model_name in _models:
            return _models[model_name]
        path = _artifact_path(model_name)
        try:
            import joblib

            loaded = joblib.load(path)
            if isinstance(loaded, dict) and model_name == "sbert":
                artifact_model = loaded.get("embedding_model")
                if artifact_model and artifact_model != SBERT_MODEL_NAME:
                    raise ValueError(
                        f"artifact uses '{artifact_model}' but runtime uses "
                        f"'{SBERT_MODEL_NAME}'"
                    )
            model = loaded.get("classifier") if isinstance(loaded, dict) else loaded
            if not hasattr(model, "predict_proba"):
                raise ValueError("artifact does not expose predict_proba")
        except Exception as exc:
            raise ArtifactUnavailableError(
                f"Model artifact '{model_name}' is unavailable at {path}: {exc}"
            ) from exc

        expected = _load_label_classes()
        classes = [str(label) for label in getattr(model, "classes_", [])]
        if classes != expected:
            raise ArtifactUnavailableError(
                f"Model '{model_name}' classes do not match label_classes.json"
            )
        _models[model_name] = model
        return model


def _validate_text(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        raise InvalidInputError("text must not be empty")
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise InvalidInputError(
            f"text must be at most {MAX_TEXT_LENGTH} characters"
        )
    return cleaned


def _probabilities(text: str, model_name: str) -> tuple[np.ndarray, list[str]]:
    cleaned = _validate_text(text)
    model = _load_model(model_name)
    if model_name == "tfidf":
        features = [cleaned]
    else:
        features = [encode_one(cleaned)]
    try:
        probabilities = np.asarray(model.predict_proba(features)[0], dtype=float)
    except Exception as exc:
        raise NLPError(f"Inference failed for model '{model_name}': {exc}") from exc
    return probabilities, [str(label) for label in model.classes_]


def predict(text: str, model_name: str = DEFAULT_MODEL) -> dict:
    probabilities, classes = _probabilities(text, model_name)
    index = int(np.argmax(probabilities))
    return {
        "intent": classes[index],
        "confidence": float(probabilities[index]),
        "model": model_name,
    }


def predict_top_k(
    text: str, model_name: str = DEFAULT_MODEL, k: int = 3
) -> list[dict]:
    if k < 1:
        raise InvalidInputError("k must be at least 1")
    probabilities, classes = _probabilities(text, model_name)
    order = np.argsort(probabilities)[::-1][: min(k, len(classes))]
    return [
        {"intent": classes[index], "confidence": float(probabilities[index])}
        for index in order
    ]


def health() -> dict:
    status = {"tfidf": False, "sbert": False, "summary": "unavailable"}
    for name in SUPPORTED_MODELS:
        try:
            _load_model(name)
            status[name] = True
        except Exception:
            status[name] = False

    try:
        from backend.nlp.summarizer import summary_status

        status["summary"] = summary_status()
    except Exception:
        status["summary"] = "unavailable"
    return status

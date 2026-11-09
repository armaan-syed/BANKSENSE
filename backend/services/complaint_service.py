from __future__ import annotations

import importlib
from datetime import datetime, timezone
from types import SimpleNamespace

from backend.config import (
    MAX_TEXT_LENGTH,
    PRIORITIES,
    SIMILAR_CASES_TOP_K,
    SUPPORTED_MODELS,
)
from backend.db import repository
from backend.db.connection import check_database
from backend.errors import (
    APIError,
    INFERENCE_ERROR,
    MODEL_UNAVAILABLE,
    UNKNOWN_MODEL,
    VALIDATION_ERROR,
)

_NLP: SimpleNamespace | None = None


def _load_nlp() -> SimpleNamespace:
    global _NLP
    if _NLP is not None:
        return _NLP

    modules: dict[str, object | None] = {}
    for name in ("predictor", "priority", "similarity", "summarizer"):
        try:
            modules[name] = importlib.import_module(f"backend.nlp.{name}")
        except ImportError:
            modules[name] = None

    if modules["predictor"] is None or modules["priority"] is None:
        raise APIError(
            503,
            MODEL_UNAVAILABLE,
            "NLP components are not available yet. Train and load the models first.",
        )

    _NLP = SimpleNamespace(**modules)
    return _NLP


def _translate_nlp_error(exc: Exception, nlp: SimpleNamespace) -> APIError:
    mapping = (
        ("InvalidInputError", 400, VALIDATION_ERROR, "text"),
        ("UnknownModelError", 400, UNKNOWN_MODEL, "model"),
        ("ArtifactUnavailableError", 503, MODEL_UNAVAILABLE, None),
    )
    for class_name, status_code, code, field in mapping:
        error_class = getattr(nlp.predictor, class_name, None)
        if error_class is not None and isinstance(exc, error_class):
            return APIError(status_code, code, str(exc) or code, field)
    return APIError(500, INFERENCE_ERROR, f"Inference failed: {exc}")


def _validate(text: str, model: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        raise APIError(400, VALIDATION_ERROR, "text must not be empty", "text")
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise APIError(
            400,
            VALIDATION_ERROR,
            f"text must be at most {MAX_TEXT_LENGTH} characters",
            "text",
        )
    if model not in SUPPORTED_MODELS:
        allowed = ", ".join(SUPPORTED_MODELS)
        raise APIError(
            400,
            UNKNOWN_MODEL,
            f"Unsupported model '{model}'. Choose one of: {allowed}",
            "model",
        )
    return cleaned


def _similar_cases(nlp: SimpleNamespace, text: str) -> list[dict]:
    if nlp.similarity is None:
        return []
    try:
        candidates = repository.fetch_candidates()
        matches = nlp.similarity.rank_similar(
            text, candidates, top_k=SIMILAR_CASES_TOP_K
        )
    except Exception:
        return []

    cases: list[dict] = []
    for match in matches:
        try:
            cases.append(
                {
                    "complaint_id": int(match["id"]),
                    "text": str(match.get("text", "")),
                    "intent": str(match.get("intent", "")),
                    "similarity": round(float(match.get("similarity", 0.0)), 4),
                    "source": match.get("source", "submitted"),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return cases


def _summary(nlp: SimpleNamespace, text: str) -> tuple[str | None, str]:
    if nlp.summarizer is None:
        return None, "unavailable"
    try:
        if nlp.summarizer.summary_status() != "enabled":
            return None, "unavailable"
        result = nlp.summarizer.summarize(text)
        if result.get("status") == "ok" and result.get("summary"):
            return str(result["summary"]), "enabled"
    except Exception:
        return None, "unavailable"
    return None, "unavailable"


def analyze(text: str, model: str) -> dict:
    cleaned = _validate(text, model)
    nlp = _load_nlp()

    try:
        prediction = nlp.predictor.predict(cleaned, model)
        intent = str(prediction["intent"])
        confidence = float(prediction["confidence"])
    except Exception as exc:
        raise _translate_nlp_error(exc, nlp) from exc

    try:
        rule = nlp.priority.suggest_priority(cleaned, intent)
        priority = str(rule["priority"])
        priority_reason = str(rule["priority_reason"])
    except Exception as exc:
        raise APIError(
            500, INFERENCE_ERROR, f"Priority rule evaluation failed: {exc}"
        ) from exc

    if priority not in PRIORITIES:
        priority = "low"
        priority_reason = "Rule matched: fallback (priority could not be determined)"

    similar_cases = _similar_cases(nlp, cleaned)
    summary, summary_status = _summary(nlp, cleaned)

    created_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    normalized_text = " ".join(cleaned.split())
    confidence = round(confidence, 4)

    complaint_id = repository.insert_complaint(
        text=cleaned,
        normalized_text=normalized_text,
        intent=intent,
        confidence=confidence,
        model=model,
        priority=priority,
        priority_reason=priority_reason,
        summary=summary,
        summary_status=summary_status,
        source="submitted",
        created_at=created_at,
    )

    return {
        "complaint_id": complaint_id,
        "text": cleaned,
        "intent": intent,
        "confidence": confidence,
        "model": model,
        "priority": priority,
        "priority_reason": priority_reason,
        "similar_cases": similar_cases,
        "summary": summary,
        "summary_status": summary_status,
        "source": "submitted",
        "created_at": created_at,
    }


def list_complaints(limit: int, offset: int) -> dict:
    rows = repository.fetch_recent(limit, offset)
    items = [
        {
            "complaint_id": row["id"],
            "text": row["text"],
            "intent": row["intent"],
            "confidence": row["confidence"],
            "model": row["model"],
            "priority": row["priority"],
            "priority_reason": row["priority_reason"],
            "similar_cases": [],
            "summary": row["summary"],
            "summary_status": row["summary_status"],
            "source": row["source"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return {"items": items, "count": len(items)}


def get_analytics() -> dict:
    return repository.analytics()


def health() -> dict:
    database = "ok"
    try:
        check_database()
    except APIError:
        database = "error"

    models = {"tfidf": False, "sbert": False}
    summary = "unavailable"
    try:
        nlp = _load_nlp()
    except APIError:
        nlp = None
    if nlp is not None:
        try:
            status = nlp.predictor.health()
            models["tfidf"] = bool(status.get("tfidf", False))
            models["sbert"] = bool(status.get("sbert", False))
        except Exception:
            pass
        if nlp.summarizer is not None:
            try:
                summary = nlp.summarizer.summary_status()
            except Exception:
                summary = "unavailable"
    if summary not in ("enabled", "unavailable"):
        summary = "unavailable"

    if database == "error":
        status_value = "error"
    elif models["tfidf"] or models["sbert"]:
        status_value = "ok"
    else:
        status_value = "degraded"

    return {
        "status": status_value,
        "models": models,
        "summary": summary,
        "database": database,
    }

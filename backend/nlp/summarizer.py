"""Optional abstractive complaint summariser.

The core submission flow never depends on this module. If the optional
transformers stack or model weights are unavailable, `summarize()` returns an
explicit `unavailable` result instead of fabricating text. Very short
complaints are returned verbatim (labelled `verbatim`) because a generative
model adds no value and may hallucinate.
"""

from __future__ import annotations

import re
import threading

from backend.nlp.config import MAX_TEXT_LENGTH, SUMMARY_MODEL_NAME

_VERBATIM_WORD_LIMIT = 30
_model = None
_tokenizer = None
_failure_reason: str | None = None
_lock = threading.Lock()


def _dependencies_available() -> tuple[bool, str]:
    try:
        import torch  # noqa: F401
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # noqa: F401
    except Exception as exc:
        return False, f"transformers stack is unavailable: {exc}"
    return True, ""


def summary_status() -> str:
    available, _ = _dependencies_available()
    return "enabled" if available else "unavailable"


def reset_summarizer() -> None:
    global _model, _tokenizer, _failure_reason
    with _lock:
        _model = None
        _tokenizer = None
        _failure_reason = None


def _unavailable(reason: str) -> dict:
    return {
        "status": "unavailable",
        "summary": None,
        "summary_status": "unavailable",
        "reason": reason,
    }


def _load_model():
    global _model, _tokenizer, _failure_reason
    if _model is not None and _tokenizer is not None:
        return _tokenizer, _model
    with _lock:
        if _model is not None and _tokenizer is not None:
            return _tokenizer, _model
        available, reason = _dependencies_available()
        if not available:
            _failure_reason = reason
            raise RuntimeError(reason)
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            _tokenizer = AutoTokenizer.from_pretrained(SUMMARY_MODEL_NAME)
            _model = AutoModelForSeq2SeqLM.from_pretrained(SUMMARY_MODEL_NAME)
            _model.eval()
        except Exception as exc:
            _failure_reason = f"summary model '{SUMMARY_MODEL_NAME}' failed to load: {exc}"
            raise RuntimeError(_failure_reason) from exc
    return _tokenizer, _model


def summarize(text: str, max_len: int = 60) -> dict:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return _unavailable("empty text")
    if len(cleaned) > MAX_TEXT_LENGTH:
        cleaned = cleaned[:MAX_TEXT_LENGTH]

    if len(cleaned.split()) <= _VERBATIM_WORD_LIMIT:
        return {
            "status": "ok",
            "summary": cleaned,
            "summary_status": "enabled",
            "method": "verbatim",
        }

    available, reason = _dependencies_available()
    if not available:
        return _unavailable(_failure_reason or reason)

    try:
        tokenizer, model = _load_model()
        import torch

        max_length = max(10, min(int(max_len), 200))
        encoded = tokenizer(
            cleaned,
            return_tensors="pt",
            truncation=True,
            max_length=1024,
        )
        with torch.no_grad():
            output = model.generate(
                **encoded,
                max_length=max_length,
                min_length=max(8, max_length // 3),
                num_beams=1,
                no_repeat_ngram_size=3,
                early_stopping=True,
            )
        summary = tokenizer.decode(output[0], skip_special_tokens=True).strip()
        summary = re.sub(r"\s+([.,!?;:])", r"\1", summary)
    except Exception as exc:
        return _unavailable(_failure_reason or f"summarisation failed: {exc}")

    if not summary:
        return _unavailable("summary model returned an empty result")
    return {
        "status": "ok",
        "summary": summary,
        "summary_status": "enabled",
        "method": "abstractive",
    }


__all__ = ["summarize", "summary_status", "reset_summarizer"]

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from backend.config import DEFAULT_MODEL


class AnalyzeRequest(BaseModel):
    text: str
    model: str = DEFAULT_MODEL


class SimilarCase(BaseModel):
    complaint_id: int
    text: str
    intent: str
    similarity: float
    source: Literal["submitted", "demo"]


class ComplaintResult(BaseModel):
    complaint_id: int
    text: str
    intent: str
    confidence: float
    model: str
    priority: str
    priority_reason: str
    similar_cases: list[SimilarCase]
    summary: str | None = None
    summary_status: Literal["enabled", "unavailable"]
    source: Literal["submitted", "demo"]
    created_at: str


class ComplaintList(BaseModel):
    items: list[ComplaintResult]
    count: int


class IntentCount(BaseModel):
    intent: str
    count: int


class PriorityCount(BaseModel):
    priority: str
    count: int


class Analytics(BaseModel):
    total_complaints: int
    by_intent: list[IntentCount]
    by_priority: list[PriorityCount]
    most_common_intents: list[IntentCount]
    includes_demo: bool


class ModelsHealth(BaseModel):
    tfidf: bool
    sbert: bool


class Health(BaseModel):
    status: Literal["ok", "degraded", "error"]
    models: ModelsHealth
    summary: Literal["enabled", "unavailable"]
    database: Literal["ok", "error"]


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail

from fastapi import APIRouter, Query

from backend.config import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from backend.schemas import AnalyzeRequest, ComplaintList, ComplaintResult
from backend.services import complaint_service

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


@router.post("/analyze", response_model=ComplaintResult)
def analyze_complaint(payload: AnalyzeRequest) -> dict:
    return complaint_service.analyze(payload.text, payload.model)


@router.get("", response_model=ComplaintList)
def list_complaints(
    limit: int = Query(default=DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return complaint_service.list_complaints(limit, offset)

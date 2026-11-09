from fastapi import APIRouter

from backend.schemas import Analytics
from backend.services import complaint_service

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics", response_model=Analytics)
def get_analytics() -> dict:
    return complaint_service.get_analytics()

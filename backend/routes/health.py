from fastapi import APIRouter

from backend.schemas import Health
from backend.services import complaint_service

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=Health)
def get_health() -> dict:
    return complaint_service.health()

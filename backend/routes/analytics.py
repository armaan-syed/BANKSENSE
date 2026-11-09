from fastapi import APIRouter, Depends

from backend.auth import CurrentUser, get_current_user
from backend.schemas import Analytics
from backend.services import complaint_service

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics", response_model=Analytics)
def get_analytics(
    user: CurrentUser | None = Depends(get_current_user),
) -> dict:
    return complaint_service.get_analytics(user=user)

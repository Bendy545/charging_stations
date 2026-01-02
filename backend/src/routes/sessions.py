from fastapi import APIRouter, Depends
from typing import Optional
from backend.src.core.dependencies import get_session_repo
from backend.src.repositories import SessionRepository
from datetime import datetime

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
async def get_sessions(
        station_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        repo: SessionRepository = Depends(get_session_repo)
):
    sessions = repo.get_all(
        station_id=station_id,
        start_date=start_date,
        end_date=end_date
    )
    return {"success": True, "data": [s.to_dict() for s in sessions]}
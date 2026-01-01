from fastapi import APIRouter, Depends
from typing import Optional
from backend.src.core.dependencies import get_session_repo
from backend.src.repositories import SessionRepository

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.get("")
async def get_sessions(
        station_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        repo: SessionRepository = Depends(get_session_repo)
):
    """Get charging sessions with optional filters"""
    try:
        data = repo.get_all(
            station_id=station_id,
            start_date=start_date,
            end_date=end_date
        )
        return {"success": True, "data": data}

    except Exception as e:
        return {"success": False, "error": str(e)}
from fastapi import APIRouter, Depends
from typing import Optional
from backend.src.core.dependencies import get_consumption_repo
from backend.src.repositories import ConsumptionRepository

router = APIRouter(prefix="/api/consumption", tags=["consumption"])

@router.get("")
async def get_consumption(
        station_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000,
        repo: ConsumptionRepository = Depends(get_consumption_repo)
):
    try:

        data = repo.get_all(
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return {"success": True, "data": data}

    except Exception as e:
        return {"success": False, "error": str(e)}
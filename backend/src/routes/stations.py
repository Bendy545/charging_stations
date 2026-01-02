from fastapi import APIRouter
from backend.src.repositories.station_repository import StationRepository
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stations", tags=["stations"])

@router.get("")
async def get_stations():
    """Get all charging stations using repository"""
    try:
        with StationRepository() as repo:
            stations = repo.get_all()
            return {
                "success": True,
                "data": [station.to_dict() for station in stations]
            }
    except Exception as e:
        logger.error(f"Error fetching stations: {e}")
        return {"success": False, "error": str(e)}

@router.get("/{station_id}")
async def get_station(station_id: int):
    """Get specific station details using repository"""
    try:
        with StationRepository() as repo:
            station = repo.get_by_id(station_id)

            if not station:
                return {"success": False, "error": "Station not found"}

            return {"success": True, "data": station.to_dict()}
    except Exception as e:
        logger.error(f"Error fetching station: {e}")
        return {"success": False, "error": str(e)}
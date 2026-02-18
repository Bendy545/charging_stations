from fastapi import APIRouter, HTTPException
from backend.src.services.sync_service import SyncService
from backend.src.repositories import StationRepository, ConsumptionRepository
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])

@router.post("/resync-station")
async def resync_station(station_id: int, days_back: int = 90):
    """
    Resync data for a specific station from scratch.
    Useful when you need to recalculate with different meter configuration.

    Example: POST /api/sync/resync-station?station_id=4&days_back=90
    """
    try:
        sync_service = SyncService()

        with StationRepository() as station_repo:
            station = station_repo.get_by_id(station_id)
            if not station:
                return {"success": False, "error": "Station not found"}

        real_station_id, real_code = sync_service._resolve_station(station.id, station.station_code)
        if real_station_id is None:
            return {"success": False, "error": "Swap target station not found"}

        logger.info(f"Starting resync for station {station.station_code} → saving as {real_code} (id={real_station_id})")

        with ConsumptionRepository() as repo:
            deleted = repo.execute(
                "DELETE FROM power_consumption WHERE station_id = %s",
                (real_station_id,)
            )

        logger.info(f"Deleted {deleted} existing records for station {station_id}")

        # Resync from scratch
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)

        logger.info(f"Fetching data from {start_time} to {end_time}")

        power_data = await sync_service.jasper_client.get_station_power_data(
            station.station_code, start_time, end_time
        )

        if not power_data:
            return {"success": False, "error": "No data returned from API"}

        with ConsumptionRepository() as repo:
            records = sync_service._process_and_save(repo, real_station_id, power_data)

        logger.info(f"Successfully added {records} records for station {station_id}")

        return {
            "success": True,
            "message": f"Resynced {records} records for station {station.station_code}",
            "station_id": station_id,
            "station_code": station.station_code,
            "records_deleted": deleted,
            "records_added": records,
            "date_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Error resyncing station: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_sync_status():
    """Get current sync status"""
    try:
        with ConsumptionRepository() as repo:
            stats = repo.get_data_stats()

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return {"success": False, "error": str(e)}
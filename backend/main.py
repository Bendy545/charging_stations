from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from backend.src.core.config import settings
from backend.src.repositories import StationRepository, ConsumptionRepository, SessionRepository, LossRepository
from backend.src.routes import stations, consumption, sessions, losses
from backend.src.services.sync_service import SyncService
from backend.src.services.scheduler import DataScheduler
from backend.src.routes import predictions
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Charging Station Loss Analysis API",
    description="API for analyzing energy losses in EV charging stations",
    version="2.0.0"
)

data_scheduler = DataScheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stations.router)
app.include_router(consumption.router)
app.include_router(sessions.router)
app.include_router(losses.router)
app.include_router(predictions.router)

@app.on_event("startup")
async def startup_event():
    """Initialize on startup using Repositories"""
    logger.info("=" * 70)
    logger.info("Starting Charging Station Loss Analysis API v2.0")
    logger.info(f"Data source: Jasper Vision API ({settings.jasper_config.get('base_url', 'N/A')})")

    try:
        with StationRepository() as station_repo:
            count = station_repo.count()
            logger.info(f"Stations configured: {count}")

        with ConsumptionRepository() as cons_repo:
            count = cons_repo.count()
            logger.info(f"Existing consumption records: {count}")

            # Pokud chceš logovat poslední data point i při startu,
            # použij novou metodu get_data_stats():
            stats = cons_repo.get_data_stats()
            if stats['last']:
                logger.info(f"Last data point: {stats['last']}")

        logger.info("Database connection successful")

    except Exception as e:
        logger.error(f"Database connection check failed: {e}")

    logger.info("")
    logger.info("Starting data scheduler...")
    data_scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    data_scheduler.stop()
    logger.info("Shutting down...")

@app.get("/")
async def root():
    return {
        "message": "Charging Station Loss Analysis API",
        "version": "2.0.0",
        "endpoints": {
            "stations": "/api/stations",
            "consumption": "/api/consumption",
            "sessions": "/api/sessions",
            "losses": "/api/losses",
            "sync_now": "/api/sync-now"
        }
    }

@app.get("/api/data-status")
async def data_status():
    """Check what data is available using Repository methods (Clean Architecture)"""
    try:
        status = {}

        with ConsumptionRepository() as repo:
            res = repo.get_data_stats()
            status["consumption"] = {
                "first_date": res['first'].isoformat() if res['first'] else None,
                "last_date": res['last'].isoformat() if res['last'] else None,
                "count": res['count']
            }

        with SessionRepository() as repo:
            res = repo.get_data_stats()
            status["sessions"] = {
                "first_date": res['first'].isoformat() if res['first'] else None,
                "last_date": res['last'].isoformat() if res['last'] else None,
                "count": res['count']
            }

        with LossRepository() as repo:
            res = repo.get_data_stats()
            status["losses"] = {
                "first_date": res['first'].isoformat() if res['first'] else None,
                "last_date": res['last'].isoformat() if res['last'] else None,
                "count": res['count']
            }

        return {"success": True, **status}

    except Exception as e:
        logger.error(f"Data status error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/sync-now")
async def sync_now():
    """Manually trigger data synchronization"""
    try:
        logger.info("Manual sync triggered via API")
        sync_service = SyncService()
        records = await sync_service.sync_all_stations()

        return {
            "success": True,
            "message": f"Synchronized {records} records",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Manual sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/initial-sync")
async def initial_sync(days_back: int = 7):
    """Perform initial historical data sync"""
    try:
        logger.info(f"Initial sync triggered: {days_back} days back")
        sync_service = SyncService()
        records = await sync_service.initial_sync(days_back)

        return {
            "success": True,
            "message": f"Initial sync completed with {records} records",
        }
    except Exception as e:
        logger.error(f"Initial sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import os
    import sys

    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    sys.path.insert(0, path)

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
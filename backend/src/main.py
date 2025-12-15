from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from backend.src.config import settings
from backend.src.database import get_db_connection
from backend.src.routes import stations, consumption, sessions, losses
from backend.src.services.sync_service import SyncService
from backend.src.services.scheduler import DataScheduler
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

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("=" * 70)
    logger.info("Starting Charging Station Loss Analysis API v2.0")
    logger.info("=" * 70)
    logger.info("Data source: Jasper Vision API")
    logger.info(f"Base URL: {settings.jasper_config['base_url']}")

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as count FROM stations")
        result = cursor.fetchone()
        logger.info(f"Stations configured: {result['count']}")

        cursor.execute("SELECT COUNT(*) as count FROM power_consumption")
        result = cursor.fetchone()
        logger.info(f"Existing consumption records: {result['count']}")

        cursor.execute("""
            SELECT MAX(timestamp) as last_timestamp 
            FROM power_consumption
        """)
        result = cursor.fetchone()
        if result and result['last_timestamp']:
            logger.info(f"Last data point: {result['last_timestamp']}")
        else:
            logger.info("No data yet - will start from 2025-11-11 08:30:00")

        cursor.close()
        connection.close()
        logger.info("Database connection successful")

    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    logger.info("")
    logger.info("Starting data scheduler...")
    logger.info("   - On startup: Backfill all missing data")
    logger.info("   - Then: Sync every 15 minutes")
    logger.info("")
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
        "data_source": "Jasper Vision API",
        "sync_interval": "15 minutes",
        "features": {
            "automatic_backfill": "On startup, syncs all missing data",
            "continuous_sync": "Every 15 minutes while running"
        },
        "endpoints": {
            "stations": "/api/stations",
            "consumption": "/api/consumption",
            "sessions": "/api/sessions",
            "losses": "/api/losses",
            "sync_now": "/api/sync-now",
            "backfill": "/api/backfill",
            "initial_sync": "/api/initial-sync",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT MAX(timestamp) as last_timestamp FROM power_consumption")
        result = cursor.fetchone()
        last_data = result['last_timestamp'] if result else None

        cursor.close()
        connection.close()

        return {
            "status": "healthy",
            "database": "connected",
            "api_configured": bool(settings.jasper_config.get("api_key")),
            "scheduler_running": data_scheduler.is_running,
            "startup_complete": data_scheduler.startup_complete,
            "last_data_timestamp": last_data.isoformat() if last_data else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

@app.post("/api/sync-now")
async def sync_now():
    """
    Manually trigger data synchronization
    Will sync from last record to now
    """
    try:
        logger.info("Manual sync triggered via API")
        sync_service = SyncService()
        records = await sync_service.sync_all_stations()

        logger.info(f"Manual sync completed: {records} records")

        return {
            "success": True,
            "message": f"Synchronized {records} records",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Manual sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backfill")
async def backfill():
    """
    Backfill any missing data from last record to now
    Same as startup backfill, but can be triggered manually
    """
    try:
        logger.info("📞 Manual backfill triggered via API")
        sync_service = SyncService()
        records = await sync_service.backfill_missing_data()

        logger.info(f"Backfill completed: {records} records")

        return {
            "success": True,
            "message": f"Backfilled {records} missing records",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Backfill error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/initial-sync")
async def initial_sync(days_back: int = 7):
    """
    Perform initial historical data sync
    Use this for first-time setup or to reload historical data

    Parameters:
    - days_back: Number of days to sync backwards (default: 7)
    """
    try:
        logger.info(f"Initial sync triggered via API: {days_back} days back")
        sync_service = SyncService()
        records = await sync_service.initial_sync(days_back)

        logger.info(f"Initial sync completed: {records} records")

        return {
            "success": True,
            "message": f"Initial sync completed with {records} records",
            "days_back": days_back,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Initial sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
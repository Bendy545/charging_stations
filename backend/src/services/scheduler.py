import asyncio
from datetime import datetime, timezone
import logging
from backend.src.services.sync_service import SyncService

logger = logging.getLogger(__name__)

class DataScheduler:
    def __init__(self):
        self.sync_service = SyncService()
        self.is_running = False
        self.sync_task = None
        self.startup_complete = False

    async def startup_backfill(self):
        """
        Run once on startup to backfill any missing data
        """
        try:
            logger.info("=" * 60)
            logger.info("STARTUP: Backfilling missing data...")
            logger.info("=" * 60)

            records = await self.sync_service.backfill_missing_data()

            if records > 0:
                logger.info(f"Startup backfill: Added {records} missing records")
            else:
                logger.info("Startup backfill: Database is up to date")

            self.startup_complete = True

        except Exception as e:
            logger.error(f"Error during startup backfill: {e}")
            self.startup_complete = True  # Continue anyway

    async def sync_task_loop(self):
        """
        Continuously sync data every 15 minutes
        """
        await self.startup_backfill()

        logger.info("=" * 60)
        logger.info("Starting scheduled sync (every 15 minutes)")
        logger.info("=" * 60)

        while self.is_running:
            try:
                now = datetime.now(timezone.utc)
                logger.info(f"⏰ Scheduled sync started: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")

                records = await self.sync_service.sync_all_stations()

                if records > 0:
                    logger.info(f"Scheduled sync: Added {records} new records")
                else:
                    logger.info("Scheduled sync: No new data available")

            except Exception as e:
                logger.error(f"Error in scheduled sync: {e}")
                import traceback
                traceback.print_exc()

            logger.info(f"Next sync in 15 minutes...")
            await asyncio.sleep(15 * 60)

    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            self.is_running = True
            self.sync_task = asyncio.create_task(self.sync_task_loop())
            logger.info("🚀 Data scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.is_running = False
            if self.sync_task:
                self.sync_task.cancel()
            logger.info("🛑 Data scheduler stopped")
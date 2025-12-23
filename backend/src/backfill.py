import asyncio
import logging
from datetime import datetime, timedelta
# Importuj tvůj upravený SyncService
from backend.src.services.sync_service import SyncService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackfillService")

async def main():
    service = SyncService()

    # Nastav datum, kdy začaly první session (podle tvých dat 24. 2. 2025)
    start_date = datetime(2025, 2, 24)
    # Končíme včerejškem
    end_date = datetime.utcnow() - timedelta(days=1)

    current = start_date
    while current <= end_date:
        day_start = current.replace(hour=0, minute=0, second=0)
        day_end = current.replace(hour=23, minute=59, second=59)

        logger.info(f">>> Stahuji data pro den: {day_start.strftime('%Y-%m-%d')}")

        try:
            records = await service.sync_all_stations_in_range(day_start, day_end)
            logger.info(f"Úspěšně uloženo {records} záznamů.")

            # Důležité: Malá pauza, abychom byli na API hodní
            await asyncio.sleep(1.5)

        except Exception as e:
            logger.error(f"Chyba u dne {day_start}: {e}")
            await asyncio.sleep(10) # Při chybě počkáme déle

        current += timedelta(days=1)

if __name__ == "__main__":
    asyncio.run(main())
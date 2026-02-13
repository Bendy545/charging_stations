from datetime import datetime, timedelta
from typing import Dict, List
import logging
from backend.src.services.jasper_client import JasperClient
from backend.src.repositories import StationRepository, ConsumptionRepository

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self):
        self.jasper_client = JasperClient()

    async def sync_station_data(self, station_id: int, station_code: str) -> int:
        """Synchronize data for a single station using Repositories"""
        try:
            with ConsumptionRepository() as consumption_repo:
                last_sync = consumption_repo.get_last_timestamp(station_id)
                if not last_sync:
                    last_sync = datetime.utcnow() - timedelta(hours=24)

                start_time = last_sync
                end_time = datetime.utcnow()

                logger.info(f"Syncing {station_code} from {start_time} to {end_time}")

                power_data = await self.jasper_client.get_station_power_data(
                    station_code, start_time, end_time
                )

                if not power_data:
                    logger.info(f"No data for station {station_code}")
                    return 0

                records_added = self._process_and_save(
                    consumption_repo, station_id, power_data
                )

                logger.info(f"Synced {records_added} records for {station_code}")
                return records_added

        except Exception as e:
            logger.error(f"Sync error {station_code}: {e}")
            return 0

    def _process_and_save(self, repo: ConsumptionRepository, station_id: int, power_data: Dict[str, List]) -> int:
        """Process raw data and save using Repository"""

        if station_id == 4:
            active_types = ['active_master']
            reactive_types = ['reactive_master']
        else:
            active_types = ['active', 'active_master']
            reactive_types = ['reactive', 'reactive_master']

        consumption_records = []

        timestamps = set()
        for p_type in active_types + reactive_types:
            if p_type in power_data:
                for item in power_data[p_type]:
                    timestamps.add(item['timeStamp'])

        for ts in sorted(timestamps):
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            active_total = 0
            reactive_total = 0

            for p_type in active_types:
                if p_type in power_data:
                    for item in power_data[p_type]:
                        if item['timeStamp'] == ts:
                            active_total += abs(float(item['value'])) * 0.25

            for p_type in reactive_types:
                if p_type in power_data:
                    for item in power_data[p_type]:
                        if item['timeStamp'] == ts:
                            reactive_total += abs(float(item['value'])) * 0.25

            consumption_records.append((dt, station_id, active_total, reactive_total))

        if consumption_records:
            return repo.bulk_upsert(consumption_records)

        return 0

    async def sync_all_stations(self) -> int:
        """Sync data for all stations"""
        total_records = 0

        with StationRepository() as station_repo:
            stations = station_repo.get_all()

        for station in stations:
            records = await self.sync_station_data(
                station.id, station.station_code
            )
            total_records += records

        logger.info(f"Total synced records: {total_records}")
        return total_records

    async def initial_sync(self, days_back: int = 7) -> int:
        """Perform initial sync for all stations"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)
        total_records = 0

        with StationRepository() as station_repo:
            stations = station_repo.get_all()

        with ConsumptionRepository() as consumption_repo:
            for station in stations:
                logger.info(f"Initial sync for {station.station_code}...")

                power_data = await self.jasper_client.get_station_power_data(
                    station.station_code, start_time, end_time
                )

                if power_data:
                    records = self._process_and_save(
                        consumption_repo, station.id, power_data
                    )
                    total_records += records
                    logger.info(f"Loaded {records} historical records for {station.station_code}")

        return total_records
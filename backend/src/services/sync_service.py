from datetime import datetime, timedelta
from typing import Dict, List
import logging
from backend.src.services.jasper_client import JasperClient
from backend.src.database import get_db_connection

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self):
        self.jasper_client = JasperClient()

    async def get_last_sync_time(self, cursor, station_id: int) -> datetime:
        cursor.execute("""
            SELECT MAX(timestamp) as last_timestamp 
            FROM power_consumption 
            WHERE station_id = %s
        """, (station_id,))

        result = cursor.fetchone()
        if result and result['last_timestamp']:
            return result['last_timestamp']
        else:
            return datetime.utcnow() - timedelta(hours=24)

    async def sync_station_data(self, station_id: int, station_code: str):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            last_sync = await self.get_last_sync_time(cursor, station_id)
            start_time = last_sync
            end_time = datetime.utcnow()

            logger.info(f"Syncing {station_code} from {start_time} to {end_time}")

            power_data = await self.jasper_client.get_station_power_data(
                station_code, start_time, end_time
            )

            if not power_data:
                logger.info(f"No data for station {station_code}")
                return 0

            records_added = await self.process_and_insert_data(
                cursor, connection, station_id, power_data
            )

            logger.info(f"Synced {records_added} records for {station_code}")
            return records_added

        except Exception as e:
            logger.error(f"Sync error {station_code}: {e}")
            connection.rollback()
            return 0
        finally:
            cursor.close()
            connection.close()

    async def process_and_insert_data(
            self, cursor, connection, station_id: int, power_data: Dict[str, List]
    ) -> int:
        interval_h = 0.25

        active_power_types = ['active', 'active_master', 'active_slave']
        reactive_power_types = ['reactive', 'reactive_master', 'reactive_slave']

        timestamps = set()
        for power_type, values in power_data.items():
            for item in values:
                timestamps.add(item['timeStamp'])

        consumption_records = []

        for ts in sorted(timestamps):
            try:
                timestamp = datetime.fromisoformat(ts.replace('Z', '+00:00'))

                active_total = 0
                reactive_total = 0

                for power_type in active_power_types:
                    if power_type in power_data:
                        for item in power_data[power_type]:
                            if item['timeStamp'] == ts:
                                value = float(item['value'])
                                active_total += value * interval_h

                for power_type in reactive_power_types:
                    if power_type in power_data:
                        for item in power_data[power_type]:
                            if item['timeStamp'] == ts:
                                value = float(item['value'])
                                reactive_total += value * interval_h

                if active_total > 0 or reactive_total > 0:
                    consumption_records.append((
                        timestamp,
                        station_id,
                        active_total,
                        reactive_total
                    ))

            except Exception as e:
                logger.error(f"Error processing timestamp {ts}: {e}")
                continue

        if consumption_records:
            try:
                cursor.executemany("""
                    INSERT INTO power_consumption 
                    (timestamp, station_id, active_power_kwh, reactive_power_kwh)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    active_power_kwh = VALUES(active_power_kwh),
                    reactive_power_kwh = VALUES(reactive_power_kwh)
                """, consumption_records)

                connection.commit()

            except Exception as e:
                logger.error(f"Error inserting records: {e}")
                connection.rollback()
                return 0

        return len(consumption_records)

    async def sync_all_stations(self):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("SELECT id, station_code FROM stations")
            stations = cursor.fetchall()

            total_records = 0

            for station in stations:
                records = await self.sync_station_data(
                    station['id'], station['station_code']
                )
                total_records += records

            logger.info(f"Total synced records: {total_records}")
            return total_records

        except Exception as e:
            logger.error(f"Error syncing all stations: {e}")
            return 0
        finally:
            cursor.close()
            connection.close()

    async def initial_sync(self, days_back: int = 7):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("SELECT id, station_code FROM stations")
            stations = cursor.fetchall()

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days_back)

            total_records = 0

            for station in stations:
                station_code = station['station_code']
                station_id = station['id']

                logger.info(f"Initial sync for {station_code}...")

                power_data = await self.jasper_client.get_station_power_data(
                    station_code, start_time, end_time
                )

                if power_data:
                    records = await self.process_and_insert_data(
                        cursor, connection, station_id, power_data
                    )
                    total_records += records
                    logger.info(f"Loaded {records} historical records for {station_code}")

            logger.info(f"Total historical records loaded: {total_records}")
            return total_records

        except Exception as e:
            logger.error(f"Error in initial sync: {e}")
            connection.rollback()
            return 0
        finally:
            cursor.close()
            connection.close()
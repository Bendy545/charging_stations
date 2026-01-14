from typing import List, Optional
from datetime import datetime
from backend.src.repositories.base import BaseRepository
from backend.src.models.consumption import PowerConsumption
import pandas as pd

class ConsumptionRepository(BaseRepository):
    """Repository for power consumption data access"""

    def get_all(
            self,
            station_id: Optional[int] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            limit: int = 1000
    ) -> List[PowerConsumption]:
        """Get power consumption data with optional filters"""
        query = """
            SELECT pc.*, s.station_code, s.station_name
            FROM power_consumption pc
            JOIN stations s ON pc.station_id = s.id
            WHERE 1=1
        """
        params = []

        if station_id:
            query += " AND pc.station_id = %s"
            params.append(station_id)

        if start_date:
            query += " AND pc.timestamp >= %s"
            params.append(start_date)

        if end_date:
            query += " AND pc.timestamp <= %s"
            params.append(end_date)

        query += " ORDER BY pc.timestamp DESC LIMIT %s"
        params.append(limit)

        rows = self.fetchall(query, tuple(params))
        return [self._row_to_model(row) for row in rows]

    def create(self, consumption: PowerConsumption) -> int:
        """Insert a new consumption record"""
        query = """
            INSERT INTO power_consumption 
            (timestamp, station_id, active_power_kwh, reactive_power_kwh)
            VALUES (%s, %s, %s, %s)
        """
        values = (
            consumption.timestamp,
            consumption.station_id,
            consumption.active_power_kwh,
            consumption.reactive_power_kwh
        )
        return self.insert(query, values)

    def bulk_upsert(self, records: List[tuple]) -> int:
        """Bulk insert or update consumption records"""
        if not records:
            return 0

        query = """
            INSERT INTO power_consumption 
            (timestamp, station_id, active_power_kwh, reactive_power_kwh)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                active_power_kwh = VALUES(active_power_kwh),
                reactive_power_kwh = VALUES(reactive_power_kwh)
        """
        return super().bulk_insert(query, records)

    def get_last_timestamp(self, station_id: int) -> Optional[datetime]:
        """Get the last recorded timestamp for a station"""
        query = """
            SELECT MAX(timestamp) as last_timestamp 
            FROM power_consumption 
            WHERE station_id = %s
        """
        result = self.fetchone(query, (station_id,))
        return result['last_timestamp'] if result else None

    def count(self) -> int:
        """Get total number of consumption records"""
        query = "SELECT COUNT(*) as count FROM power_consumption"
        result = self.fetchone(query)
        return result['count'] if result else 0

    def _row_to_model(self, row: dict) -> PowerConsumption:
        """Convert database row to domain model"""
        return PowerConsumption(
            id=row['id'],
            timestamp=row['timestamp'],
            station_id=row['station_id'],
            active_power_kwh=float(row['active_power_kwh']),
            reactive_power_kwh=float(row['reactive_power_kwh']),
            station_code=row.get('station_code'),
            station_name=row.get('station_name')
        )

    def get_data_stats(self) -> dict:
        """Get aggregate statistics for data availability"""
        query = """
            SELECT 
                MIN(timestamp) as first, 
                MAX(timestamp) as last, 
                COUNT(*) as count 
            FROM power_consumption
        """
        result = self.fetchone(query)
        return result if result else {'first': None, 'last': None, 'count': 0}

    def get_for_training(self, exclude_ids: List[int], station_id: Optional[int] = None) -> List[dict]:
        query = "SELECT timestamp, station_id, active_power_kwh, reactive_power_kwh FROM power_consumption WHERE station_id NOT IN (%s)"
        params = [tuple(exclude_ids)]
        query = f"SELECT timestamp, station_id, active_power_kwh, reactive_power_kwh FROM power_consumption WHERE station_id NOT IN ({','.join(['%s']*len(exclude_ids))})"
        params = list(exclude_ids)

        if station_id:
            query += " AND station_id = %s"
            params.append(station_id)
        return self.fetchall(query, tuple(params))
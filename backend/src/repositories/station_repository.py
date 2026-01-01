from typing import List, Optional
from backend.src.repositories.base import BaseRepository
from backend.src.models.station import Station
import logging

logger = logging.getLogger(__name__)

class StationRepository(BaseRepository):
    """Repository for station data access"""

    def get_all(self) -> List[Station]:
        """Get all charging stations"""
        query = "SELECT * FROM stations ORDER BY station_code"
        rows = self.fetchall(query)
        return [self._row_to_model(row) for row in rows]

    def get_by_id(self, station_id: int) -> Optional[Station]:
        """Get a single station by ID"""
        query = "SELECT * FROM stations WHERE id = %s"
        row = self.fetchone(query, (station_id,))
        return self._row_to_model(row) if row else None

    def get_by_code(self, station_code: str) -> Optional[Station]:
        """Get a single station by station code"""
        query = "SELECT * FROM stations WHERE station_code = %s"
        row = self.fetchone(query, (station_code,))
        return self._row_to_model(row) if row else None

    def get_id_by_code(self, station_code: str) -> Optional[int]:
        """Get station ID by station code (optimized query)"""
        query = "SELECT id FROM stations WHERE station_code = %s"
        row = self.fetchone(query, (station_code,))
        return row['id'] if row else None

    def get_code_to_id_map(self) -> dict:
        """Get mapping of station_code -> station_id"""
        query = "SELECT id, station_code FROM stations"
        rows = self.fetchall(query)
        return {row['station_code']: row['id'] for row in rows}

    def create(self, station: Station) -> int:
        """
        Insert a new station.

        Returns:
            ID of newly created station
        """
        query = """
            INSERT INTO stations (station_code, station_name, location)
            VALUES (%s, %s, %s)
        """
        values = (station.station_code, station.station_name, station.location)
        return self.insert(query, values)

    def update(self, station: Station) -> bool:
        """
        Update an existing station.

        Returns:
            True if station was updated
        """
        query = """
            UPDATE stations 
            SET station_name = %s, location = %s
            WHERE id = %s
        """
        values = (station.station_name, station.location, station.id)
        rows_affected = self.execute(query, values)
        return rows_affected > 0

    def delete(self, station_id: int) -> bool:
        """
        Delete a station.

        Returns:
            True if station was deleted
        """
        query = "DELETE FROM stations WHERE id = %s"
        rows_affected = self.execute(query, (station_id,))
        return rows_affected > 0

    def count(self) -> int:
        """Get total number of stations"""
        query = "SELECT COUNT(*) as count FROM stations"
        result = self.fetchone(query)
        return result['count'] if result else 0

    def _row_to_model(self, row: dict) -> Station:
        """Convert database row to domain model"""
        return Station(
            id=row['id'],
            station_code=row['station_code'],
            station_name=row['station_name'],
            location=row.get('location', 'Jeníšov'),
            created_at=row.get('created_at')
        )
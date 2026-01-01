from typing import List, Optional
from datetime import datetime
from backend.src.repositories.base import BaseRepository
from backend.src.models.session import ChargingSession

class SessionRepository(BaseRepository):
    """Repository for charging session data access"""

    def get_all(
            self,
            station_id: Optional[int] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            limit: int = 1000
    ) -> List[ChargingSession]:
        """Get charging sessions with optional filters"""
        query = """
            SELECT cs.*, s.station_code, s.station_name
            FROM charging_sessions cs
            JOIN stations s ON cs.station_id = s.id
            WHERE 1=1
        """
        params = []

        if station_id:
            query += " AND cs.station_id = %s"
            params.append(station_id)

        if start_date:
            query += " AND cs.end_interval_15min >= %s"
            params.append(start_date)

        if end_date:
            query += " AND cs.end_interval_15min <= %s"
            params.append(end_date)

        query += " ORDER BY cs.end_interval_15min DESC LIMIT %s"
        params.append(limit)

        rows = self.fetchall(query, tuple(params))
        return [self._row_to_model(row) for row in rows]

    def get_by_id(self, session_id: int) -> Optional[ChargingSession]:
        """Get a single session by ID"""
        query = """
            SELECT cs.*, s.station_code, s.station_name
            FROM charging_sessions cs
            JOIN stations s ON cs.station_id = s.id
            WHERE cs.id = %s
        """
        row = self.fetchone(query, (session_id,))
        return self._row_to_model(row) if row else None

    def create(self, session: ChargingSession) -> int:
        """Insert a new session"""
        query = """
            INSERT INTO charging_sessions 
            (station_id, charger_name, start_date, end_date, 
             total_kwh, start_card, end_interval_15min)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            session.station_id,
            session.charger_name,
            session.start_date,
            session.end_date,
            session.total_kwh,
            session.start_card,
            session.end_interval_15min
        )
        return self.insert(query, values)

    def bulk_insert(self, sessions: List[ChargingSession]) -> int:
        """Bulk insert sessions"""
        if not sessions:
            return 0

        query = """
            INSERT INTO charging_sessions 
            (station_id, charger_name, start_date, end_date, 
             total_kwh, start_card, end_interval_15min)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = [
            (s.station_id, s.charger_name, s.start_date, s.end_date,
             s.total_kwh, s.start_card, s.end_interval_15min)
            for s in sessions
        ]
        return super().bulk_insert(query, values)

    def count(self) -> int:
        """Get total number of sessions"""
        query = "SELECT COUNT(*) as count FROM charging_sessions"
        result = self.fetchone(query)
        return result['count'] if result else 0

    def _row_to_model(self, row: dict) -> ChargingSession:
        """Convert database row to domain model"""
        return ChargingSession(
            id=row['id'],
            station_id=row['station_id'],
            charger_name=row['charger_name'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            total_kwh=float(row['total_kwh']),
            start_card=row.get('start_card', ''),
            end_interval_15min=row.get('end_interval_15min'),
            station_code=row.get('station_code'),
            station_name=row.get('station_name')
        )

    def get_data_stats(self) -> dict:
        """Get aggregate statistics for data availability"""
        query = """
            SELECT 
                MIN(end_date) as first, 
                MAX(end_date) as last, 
                COUNT(*) as count 
            FROM charging_sessions
        """
        result = self.fetchone(query)
        return result if result else {'first': None, 'last': None, 'count': 0}
from fastapi import APIRouter
from typing import Optional
from backend.src.database import get_db_connection

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.get("")
async def get_sessions(
        station_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
):
    """Get charging sessions with optional filters"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

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

    try:
        cursor.execute(query, params)
        sessions = cursor.fetchall()
        return {"success": True, "data": sessions}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()
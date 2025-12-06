from fastapi import APIRouter
from typing import Optional
from backend.src.database import get_db_connection

router = APIRouter(prefix="/api/consumption", tags=["consumption"])

@router.get("")
async def get_consumption(
        station_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
):
    """Get power consumption data with optional filters"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

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

    try:
        cursor.execute(query, params)
        consumption = cursor.fetchall()
        return {"success": True, "data": consumption}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()
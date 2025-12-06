from fastapi import APIRouter
from typing import Optional
from backend.src.database import get_db_connection
from backend.src.services.loss_calculator import calculate_losses

router = APIRouter(prefix="/api/losses", tags=["losses"])

@router.get("")
async def get_losses(
        station_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
):
    """Get loss analysis data"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT la.*, s.station_code, s.station_name
        FROM loss_analysis la
        JOIN stations s ON la.station_id = s.id
        WHERE 1=1
    """
    params = []

    if station_id:
        query += " AND la.station_id = %s"
        params.append(station_id)

    if start_date:
        query += " AND la.period_start >= %s"
        params.append(start_date)

    if end_date:
        query += " AND la.period_end <= %s"
        params.append(end_date)

    query += " ORDER BY la.period_start DESC"

    try:
        cursor.execute(query, params)
        losses = cursor.fetchall()
        return {"success": True, "data": losses}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()

@router.post("/recalculate")
async def recalculate_losses():
    """Manually trigger loss recalculation"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        calculate_losses(cursor, connection)
        return {"success": True, "message": "Losses recalculated successfully"}
    except Exception as e:
        connection.rollback()
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()
from fastapi import APIRouter
from backend.src.database import get_db_connection

router = APIRouter(prefix="/api/stations", tags=["stations"])

@router.get("")
async def get_stations():
    """Get all charging stations"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM stations ORDER BY station_code")
        stations = cursor.fetchall()
        return {"success": True, "data": stations}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()

@router.get("/{station_id}")
async def get_station(station_id: int):
    """Get specific station details"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM stations WHERE id = %s", (station_id,))
        station = cursor.fetchone()
        if not station:
            return {"success": False, "error": "Station not found"}
        return {"success": True, "data": station}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()
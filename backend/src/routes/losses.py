from fastapi import APIRouter, HTTPException
from typing import Optional
from backend.src.database import get_db_connection
from backend.src.services.proper_loss_calculator import (
    recalculate_everything,
    get_data_quality_report
)
import logging

logger = logging.getLogger(__name__)

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
    """
    PROPER loss recalculation with session energy distribution
    This is the CORRECT method that fixes negative losses
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        logger.info("🔄 Manual recalculation triggered via API")

        recalculate_everything(cursor, connection)

        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                MIN(period_start) as first_date,
                MAX(period_end) as last_date,
                AVG(loss_percentage) as avg_loss_pct
            FROM loss_analysis
        """)
        summary = cursor.fetchone()

        return {
            "success": True,
            "message": "Losses recalculated with proper session distribution",
            "summary": {
                "total_records": summary['total_records'],
                "date_range": f"{summary['first_date']} to {summary['last_date']}",
                "average_loss_percentage": round(summary['avg_loss_pct'], 2)
            }
        }
    except Exception as e:
        logger.error(f"❌ Recalculation error: {e}")
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@router.get("/quality-report")
async def quality_report():
    """
    Get data quality report showing potential issues
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        report = get_data_quality_report(cursor)
        return {
            "success": True,
            "report": report
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()


@router.get("/distributed-sessions")
async def get_distributed_sessions(
        station_id: Optional[int] = None,
        limit: int = 100
):
    """
    View distributed session data (for debugging)
    Shows how session energy was distributed across intervals
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT 
            ds.*,
            cs.start_date,
            cs.end_date,
            cs.total_kwh as session_total,
            s.station_code,
            s.station_name
        FROM distributed_sessions ds
        JOIN charging_sessions cs ON ds.session_id = cs.id
        JOIN stations s ON ds.station_id = s.id
        WHERE 1=1
    """
    params = []

    if station_id:
        query += " AND ds.station_id = %s"
        params.append(station_id)

    query += " ORDER BY ds.interval_15min DESC LIMIT %s"
    params.append(limit)

    try:
        cursor.execute(query, params)
        data = cursor.fetchall()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        connection.close()
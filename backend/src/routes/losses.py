from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import date, datetime, timedelta

from backend.src.services.loss_calculator_service import LossCalculatorService
from backend.src.services.power_analysis_service import PowerAnalysisService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/losses", tags=["losses"])

loss_service = LossCalculatorService()
power_service = PowerAnalysisService()

@router.get("")
async def get_losses(
        station_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
):
    """Get loss analysis data using service layer"""
    try:
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None

        losses = loss_service.get_losses(
            station_id=station_id,
            start_date=start,
            end_date=end
        )

        return {
            "success": True,
            "data": [loss.to_dict() for loss in losses]
        }
    except Exception as e:
        logger.error(f"Error fetching losses: {e}")
        return {"success": False, "error": str(e)}

@router.post("/recalculate")
async def recalculate_losses():
    try:
        result = loss_service.recalculate_all()
        return {
            "success": True,
            "message": "Přepočet dokončen",
            "summary": result
        }
    except Exception as e:
        logger.error(f"Chyba při přepočtu: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_statistics(
        station_id: Optional[int] = None,
        exclude_problematic: bool = True
):
    """Get aggregate statistics using service"""
    try:
        stats = loss_service.get_statistics(
            station_id=station_id,
            exclude_problematic=exclude_problematic
        )
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"success": False, "error": str(e)}

@router.get("/power-factor")
async def get_power_factor(station_id: Optional[int] = None):
    """Get power factor analysis"""
    try:
        analysis = power_service.get_power_factor_analysis(station_id)

        if analysis is None:
            return {"success": False, "message": "No data available"}

        return {"success": True, "data": analysis}
    except Exception as e:
        logger.error(f"Error calculating power factor: {e}")
        return {"success": False, "error": str(e)}

@router.get("/power-factor/by-station")
async def get_power_factor_by_station():
    """Get power factor for all stations"""
    try:
        results = power_service.get_power_factor_by_station()
        return {"success": True, "data": results}
    except Exception as e:
        logger.error(f"Error getting power factor by station: {e}")
        return {"success": False, "error": str(e)}

@router.get("/diagnose")
async def diagnose_data(
        test_date: str = "2025-11-27",
        station_id: int = 7
):
    """Diagnostic endpoint to check data quality"""
    from backend.src.repositories.loss_repository import LossRepository

    with LossRepository() as repo:
        repo.diagnose_data(test_date, station_id)

    return {"success": True, "message": "Check server logs for diagnostic output"}

@router.get("/power-factor/trend")
async def get_power_factor_trend(
        station_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        mode: str = "active",
        threshold: float = 0.5
):
    """
    Get power factor trend over time for a station.

    Parameters:
    - station_id: Station to analyze
    - start_date: Start date (ISO format)
    - end_date: End date (ISO format)
    - mode: "active" (filter low power) or "all" (include standby)
    - threshold: Minimum kWh per 15-min interval to consider (default 0.5 = ~2kW avg)
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else loss_service.loss_repo.SESSION_DATA_START
        end_dt = (datetime.fromisoformat(end_date) + timedelta(days=1)) if end_date else (loss_service.loss_repo.SESSION_DATA_END + timedelta(days=1))

        with loss_service.loss_repo as repo:
            rows = repo.get_power_factor_trend_pc(
                station_id=station_id,
                start_dt=start_dt,
                end_dt=end_dt,
                mode=mode,
                active_threshold_kwh=threshold,
            )

        # UI-friendly shape
        data = [
            {
                "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                "powerFactor": float(row["power_factor"]) if row["power_factor"] is not None else 0.0,
                "totalActive": float(row.get("total_active", 0)),
                "totalReactive": float(row.get("total_reactive", 0))
            }
            for row in rows
        ]

        return {"success": True, "data": data, "periods_count": len(data)}
    except Exception as e:
        logger.error(f"Error getting power factor trend: {e}")
        return {"success": False, "error": str(e)}

@router.get("/power-factor/by-station-v2")
async def get_power_factor_by_station_v2(
        mode: str = "active",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        threshold: float = 0.5,  # Changed from 0.05 to 0.5
):
    """
    Get power factor for all stations with filtering.

    Parameters:
    - mode: "active" (exclude standby) or "all" (include everything)
    - start_date: Start date (ISO format)
    - end_date: End date (ISO format)
    - threshold: Minimum kWh per 15-min interval (default 0.5 = ~2kW avg power)
    """
    try:
        start = datetime.fromisoformat(start_date) if start_date else loss_service.loss_repo.SESSION_DATA_START
        if end_date:
            end = datetime.fromisoformat(end_date) + timedelta(days=1)
        else:
            end = loss_service.loss_repo.SESSION_DATA_END + timedelta(days=1)

        with loss_service.loss_repo as repo:
            data = repo.get_power_factor_by_station_pc(start, end, mode=mode, active_threshold_kwh=threshold)

        # Add interpretation to each station
        for station in data:
            pf = station.get('power_factor', 0)
            if pf >= 95:
                station['status'] = 'excellent'
            elif pf >= 85:
                station['status'] = 'good'
            elif pf >= 70:
                station['status'] = 'fair'
            else:
                station['status'] = 'poor'

        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error getting power factor by station v2: {e}")
        return {"success": False, "error": str(e)}
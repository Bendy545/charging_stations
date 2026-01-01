from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import date
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
        # Convert string dates to date objects if provided
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None

        # Use service to get losses
        losses = loss_service.get_losses(
            station_id=station_id,
            start_date=start,
            end_date=end
        )

        # Convert to dict for JSON response
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
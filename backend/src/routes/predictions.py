"""
Predictions API Router
======================
This provides API endpoints to train models and get predictions.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from backend.src.services.prediction_service import HourlyPredictionService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

# Initialize prediction service (using your proven hourly approach!)
prediction_service = HourlyPredictionService()


@router.post("/train")
async def train_model(station_id: Optional[int] = None):
    """
    Train the prediction model

    Example: POST /api/predictions/train?station_id=3

    This trains the model on historical data. You should run this:
    - When you first set up the system
    - Periodically (e.g., once a week) to update the model with new data
    """
    try:
        logger.info(f"Training model for station_id={station_id}")
        results = prediction_service.train_model(station_id=station_id)

        return {
            "success": True,
            "message": "Model trained successfully",
            "results": results
        }

    except ValueError as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast")
async def get_forecast(station_id: int, days: int = 7):
    """
    Get daily loss predictions for the next N days

    Example: GET /api/predictions/forecast?station_id=3&days=7

    Returns:
        Daily aggregated predictions with dates and expected loss
    """
    try:
        if days < 1 or days > 30:
            raise ValueError("Days must be between 1 and 30")

        logger.info(f"Getting {days}-day forecast for station {station_id}")
        predictions = prediction_service.predict_daily_summary(station_id, days)

        return {
            "success": True,
            "station_id": station_id,
            "forecast_days": days,
            "predictions": predictions
        }

    except ValueError as e:
        logger.error(f"Forecast error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast/hourly")
async def get_hourly_forecast(station_id: int, hours: int = 24):
    """
    Get hourly loss predictions for the next N hours

    Example: GET /api/predictions/forecast/hourly?station_id=3&hours=24

    Returns:
        Hourly predictions with timestamps and expected loss in kWh
    """
    try:
        if hours < 1 or hours > 168:  # Max 1 week
            raise ValueError("Hours must be between 1 and 168 (1 week)")

        logger.info(f"Getting {hours}-hour forecast for station {station_id}")
        predictions = prediction_service.predict_next_hours(station_id, hours)

        return {
            "success": True,
            "station_id": station_id,
            "forecast_hours": hours,
            "predictions": predictions
        }

    except ValueError as e:
        logger.error(f"Hourly forecast error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting hourly forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-info")
async def get_model_info():
    """
    Get information about the current model

    Example: GET /api/predictions/model-info

    Returns:
        Model status, type, and coefficients
    """
    try:
        info = prediction_service.get_model_info()
        return {
            "success": True,
            "model_info": info
        }
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_predictions(station_id: int, date: str):
    try:
        # TODO: Implement comparison logic
        # This would fetch actual loss for the date and compare with prediction
        return {
            "success": True,
            "message": "Comparison feature coming soon"
        }
    except Exception as e:
        logger.error(f"Error comparing predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
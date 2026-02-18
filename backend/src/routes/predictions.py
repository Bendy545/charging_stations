from fastapi import APIRouter, HTTPException
from typing import Optional
from backend.src.services.prediction_service import PredictionService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

prediction_service = PredictionService()


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
        results = prediction_service.train_model(station_id=station_id)

        target_stations = [1, 2, 3, 4, 5, 6, 7] if station_id is None else [station_id]

        prediction_service.refresh_cache_for_stations(target_stations)

        return {
            "success": True,
            "message": "Model trained and cache refreshed",
            "results": results
        }
    except Exception as e:
        logger.error(f"Unexpected error during training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast")
async def get_forecast(station_id: int, days: int = 7):
    predictions = prediction_service.get_forecast_from_cache(station_id, days)

    if not predictions:
        raise HTTPException(status_code=404, detail="No cached predictions found. Please train the model.")

    return {"success": True, "predictions": predictions}

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


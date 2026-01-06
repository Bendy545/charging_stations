"""
Predictions API Router
======================
This provides API endpoints to train models and get predictions.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from backend.src.services.prediction_service import PredictionService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

prediction_service = PredictionService()


@router.post("/train")
async def train_model(station_id: Optional[int] = None):
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
    try:
        if days < 1 or days > 30:
            raise ValueError("Days must be between 1 and 30")

        logger.info(f"Getting {days}-day forecast for station {station_id}")
        predictions = prediction_service.predict_next_days(station_id, days)

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


@router.get("/model-info")
async def get_model_info():
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
        return {
            "success": True,
            "message": "Comparison feature coming soon"
        }
    except Exception as e:
        logger.error(f"Error comparing predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
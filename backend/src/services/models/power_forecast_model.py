import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from typing import Dict, List, Optional
import logging
import pickle
import os

logger = logging.getLogger(__name__)


class PowerForecastModel:
    """
    Model 1 of 2: Predicts how much energy (kWh) a station will consume.

    Learns patterns like:
    - "Station 5 typically draws 12 kWh at 3pm on a Tuesday"
    - "Weekend consumption is lower across all stations"
    - "When delivered energy is high, total consumption is proportionally higher"

    This model provides the consumption baseline that the LossRateModel
    then applies a loss percentage to.
    """

    FEATURE_NAMES = [
        'hour', 'day_of_week', 'is_weekend',
        'hour_sin', 'hour_cos',
        'day_of_week_sin', 'day_of_week_cos',
        'station_id',
        'delivered_kwh'
    ]

    def __init__(self, model_path: str = "models/power_forecast_model.pkl"):
        self.model: Optional[RandomForestRegressor] = None
        self.feature_names: List[str] = self.FEATURE_NAMES
        self.model_path = model_path

    def train(self, df: pd.DataFrame) -> Dict:
        """
        Train the power forecast model on prepared feature data.

        Args:
            df: DataFrame with features and 'consumption_kwh' target

        Returns:
            Training results dict with metrics
        """
        X = df[self.feature_names]
        y = df['consumption_kwh']

        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]

        logger.info(f"⚡ POWER FORECAST MODEL:")
        logger.info(f"  Training samples: {len(X)}")
        logger.info(f"  Target range: {y.min():.2f} - {y.max():.2f} kWh")

        tscv = TimeSeriesSplit(n_splits=5)

        self.model = RandomForestRegressor(
            n_estimators=150,
            max_depth=15,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1
        )

        cv_scores = cross_val_score(
            self.model, X, y,
            cv=tscv, scoring='neg_mean_absolute_error'
        )
        cv_mae = -cv_scores.mean()
        logger.info(f"  CV MAE: {cv_mae:.3f} kWh")

        self.model.fit(X, y)

        return {
            'cv_mae_kwh': round(cv_mae, 3)
        }

    def predict(self, features: pd.DataFrame) -> float:
        """
        Predict consumption for a single hour.

        Args:
            features: Single-row DataFrame with all required features

        Returns:
            Predicted consumption in kWh (clamped to >= 0)
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")

        X = features[self.feature_names]
        prediction = self.model.predict(X)[0]
        return max(0.0, prediction)

    def save(self):
        """Save model to disk"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names
            }, f)
        logger.info(f"Power forecast model saved to {self.model_path}")

    def load(self) -> bool:
        """Load model from disk. Returns True if successful."""
        if not os.path.exists(self.model_path):
            logger.warning(f"No saved model at {self.model_path}")
            return False

        with open(self.model_path, 'rb') as f:
            saved = pickle.load(f)
            self.model = saved['model']
            self.feature_names = saved['feature_names']
        logger.info(f"Power forecast model loaded from {self.model_path}")
        return True

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def get_info(self) -> Dict:
        """Get model metadata"""
        if not self.is_ready:
            return {'status': 'not_trained'}
        return {
            'status': 'ready',
            'n_estimators': self.model.n_estimators,
            'n_features': len(self.feature_names),
            'features': self.feature_names
        }
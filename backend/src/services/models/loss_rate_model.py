import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
from typing import Dict, List, Optional
import logging
import pickle
import os

logger = logging.getLogger(__name__)


class LossRateModel:
    """
    Model 2 of 2: Predicts what PERCENTAGE of consumed energy will be lost.

    Learns patterns like:
    - "When reactive power is high and charging activity is low, losses are ~8%"
    - "Losses tend to be higher during standby periods"
    - "Station X has consistently higher losses than Station Y"

    Trained WITHOUT active_power as a feature to avoid data leakage —
    at prediction time we don't know future consumption, so we can't use it.
    """

    FEATURE_NAMES = [
        'delivered_kwh',
        'reactive_power_kvar',
        'power_factor',
        'reactive_ratio',
        'hour', 'day_of_week', 'is_weekend',
        'hour_sin', 'hour_cos',
        'day_of_week_sin', 'day_of_week_cos',
        'loss_pct_lag_1h',
        'loss_pct_lag_24h',
        'loss_pct_rolling_mean',
        'loss_pct_rolling_std',
        'station_id',
        'station_quality'
    ]

    def __init__(self, model_path: str = "models/loss_rate_model.pkl"):
        self.model: Optional[RandomForestRegressor] = None
        self.feature_names: List[str] = self.FEATURE_NAMES
        self.model_path = model_path

    def train(self, df: pd.DataFrame) -> Dict:
        """
        Train the loss rate model on prepared feature data.

        Args:
            df: DataFrame with all features already computed (from create_features)

        Returns:
            Training results dict with metrics
        """
        X = df[self.feature_names]
        y = df['loss_percentage']

        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]

        logger.info(f"📊 LOSS RATE MODEL:")
        logger.info(f"  Training samples: {len(X)}")
        logger.info(f"  Features: {len(self.feature_names)}")
        logger.info(f"  Target range: {y.min():.2f}% - {y.max():.2f}%")

        tscv = TimeSeriesSplit(n_splits=5)

        self.model = RandomForestRegressor(
            n_estimators=200,
            max_depth=20,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1
        )

        cv_scores = cross_val_score(
            self.model, X, y,
            cv=tscv, scoring='neg_mean_absolute_error'
        )
        cv_mae = -cv_scores.mean()
        logger.info(f"  CV MAE: {cv_mae:.3f} ± {cv_scores.std():.3f} %")

        self.model.fit(X, y)

        train_idx, test_idx = list(tscv.split(X))[-1]
        y_pred_test = self.model.predict(X.iloc[test_idx])
        test_mae = mean_absolute_error(y.iloc[test_idx], y_pred_test)
        test_r2 = r2_score(y.iloc[test_idx], y_pred_test)

        importance = dict(zip(self.feature_names, self.model.feature_importances_))
        importance = {k: round(v, 4) for k, v in sorted(importance.items(), key=lambda x: x[1], reverse=True)}

        logger.info(f"  Test MAE: {test_mae:.3f}%, R²: {test_r2:.4f}")
        logger.info(f"  Top features:")
        for feat, imp in list(importance.items())[:5]:
            logger.info(f"    {feat}: {imp:.4f}")

        return {
            'test_mae_pct': round(test_mae, 3),
            'test_r2': round(test_r2, 4),
            'cv_mae': round(cv_mae, 3),
            'feature_importance': importance
        }

    def predict(self, features: pd.DataFrame) -> float:
        """
        Predict loss percentage for a single hour.

        Args:
            features: Single-row DataFrame with all required features

        Returns:
            Predicted loss percentage (clamped to 0-100)
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")

        X = features[self.feature_names]
        prediction = self.model.predict(X)[0]
        return max(0.0, min(100.0, prediction))

    def save(self):
        """Save model to disk"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names
            }, f)
        logger.info(f"Loss rate model saved to {self.model_path}")

    def load(self) -> bool:
        """Load model from disk. Returns True if successful."""
        if not os.path.exists(self.model_path):
            logger.warning(f"No saved model at {self.model_path}")
            return False

        with open(self.model_path, 'rb') as f:
            saved = pickle.load(f)
            self.model = saved['model']
            self.feature_names = saved['feature_names']
        logger.info(f"Loss rate model loaded from {self.model_path}")
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
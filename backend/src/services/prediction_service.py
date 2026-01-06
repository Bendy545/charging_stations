"""
Robust Loss Prediction Service
================================
Handles messy real-world data with filtering and validation
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import pickle
import os

from backend.src.repositories.loss_repository import LossRepository

logger = logging.getLogger(__name__)


class PredictionService:
    def __init__(self):
        self.loss_repo = LossRepository()
        self.model = None
        self.model_path = "models/loss_prediction_model.pkl"

    def clean_data(self, loss_data: List) -> pd.DataFrame:
        df = pd.DataFrame([{
            'date': l.period_start,
            'station_id': l.station_id,
            'loss_percentage': float(l.loss_percentage),
            'total_consumption': float(l.total_consumption_kwh),
            'total_delivered': float(l.total_delivered_kwh),
            'power_factor': l.power_factor,
            'total_reactive': float(l.total_reactive_kwh)
        } for l in loss_data])

        initial_count = len(df)
        logger.info(f"Starting with {initial_count} records")

        df = df[df['total_delivered'] > 0]
        logger.info(f"  After removing zero deliveries: {len(df)} records ({initial_count - len(df)} removed)")

        df = df[df['loss_percentage'] >= 0]
        logger.info(f"  After removing negative losses: {len(df)} records")

        df = df[df['loss_percentage'] <= 30]  # Normal EV charging losses are 5-20%
        logger.info(f"  After removing extreme losses (>30%): {len(df)} records")

        df = df[df['total_consumption'] >= 10]
        logger.info(f"  After requiring min consumption: {len(df)} records")

        df = df[df['power_factor'].between(50, 100)]
        logger.info(f"  After power factor filter: {len(df)} records")

        if len(df) < 30:
            raise ValueError(f"After cleaning, only {len(df)} valid records remain. Need at least 30!")

        logger.info(f"✓ Cleaned data: {len(df)}/{initial_count} records kept ({len(df)/initial_count*100:.1f}%)")

        return df

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:

        df = df.sort_values(['station_id', 'date']).copy()

        df['loss_yesterday'] = df.groupby('station_id')['loss_percentage'].shift(1)

        df['loss_7day_avg'] = df.groupby('station_id')['loss_percentage'].transform(
            lambda x: x.rolling(window=7, min_periods=3).mean().shift(1)
        )

        df['day_of_week'] = pd.to_datetime(df['date']).dt.dayofweek

        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

        df['power_factor_7day_avg'] = df.groupby('station_id')['power_factor'].transform(
            lambda x: x.rolling(window=7, min_periods=3).mean().shift(1)
        )

        df['consumption_7day_avg'] = df.groupby('station_id')['total_consumption'].transform(
            lambda x: x.rolling(window=7, min_periods=3).mean().shift(1)
        )

        df['consumption_7day_std'] = df.groupby('station_id')['total_consumption'].transform(
            lambda x: x.rolling(window=7, min_periods=3).std().shift(1)
        )

        df = df.dropna()

        logger.info(f"✓ Features created: {len(df)} records with complete features")

        return df

    def train_model(self, station_id: Optional[int] = None, min_loss: float = 0, max_loss: float = 30) -> Dict:
        logger.info(f"="*60)
        logger.info(f"Training model with data filtering")
        logger.info(f"  Station: {station_id if station_id else 'ALL'}")
        logger.info(f"  Loss range: {min_loss}% - {max_loss}%")
        logger.info(f"="*60)

        with self.loss_repo as repo:
            loss_data = repo.get_all(station_id=station_id)

        if len(loss_data) < 30:
            raise ValueError(f"Not enough raw data: {len(loss_data)} records")

        try:
            df_clean = self.clean_data(loss_data)
        except ValueError as e:
            raise ValueError(f"Data cleaning failed: {e}")

        df_clean = df_clean[
            (df_clean['loss_percentage'] >= min_loss) &
            (df_clean['loss_percentage'] <= max_loss)
            ]

        if len(df_clean) < 20:
            raise ValueError(f"After all filters, only {len(df_clean)} records remain")

        df = self.prepare_features(df_clean)

        if len(df) < 15:
            raise ValueError(f"After feature engineering: only {len(df)} records")

        feature_columns = [
            'loss_yesterday',
            'loss_7day_avg',
            'day_of_week',
            'is_weekend',
            'power_factor_7day_avg',
            'consumption_7day_avg',
            'consumption_7day_std'
        ]

        X = df[feature_columns]
        y = df['loss_percentage']

        logger.info(f"\n📊 Training Data Summary:")
        logger.info(f"  Records: {len(df)}")
        logger.info(f"  Loss range: {y.min():.2f}% - {y.max():.2f}%")
        logger.info(f"  Loss mean: {y.mean():.2f}%")
        logger.info(f"  Loss std: {y.std():.2f}%")

        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        logger.info(f"\n  Train: {len(X_train)} samples")
        logger.info(f"  Test: {len(X_test)} samples")

        self.model = LinearRegression()
        self.model.fit(X_train, y_train)

        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)

        mae_train = mean_absolute_error(y_train, y_pred_train)
        mae_test = mean_absolute_error(y_test, y_pred_test)
        r2_train = r2_score(y_train, y_pred_train)
        r2_test = r2_score(y_test, y_pred_test)

        baseline_mae = mean_absolute_error(y_test, [y_train.mean()] * len(y_test))
        improvement = ((baseline_mae - mae_test) / baseline_mae * 100)

        self._save_model()

        if mae_test < 2.0 and r2_test > 0.5:
            quality = "Excellent ⭐⭐⭐"
        elif mae_test < 4.0 and r2_test > 0.3:
            quality = "Good ⭐⭐"
        elif mae_test < 6.0 and r2_test > 0.1:
            quality = "Fair ⭐"
        else:
            quality = "Poor - Needs more/better data"

        results = {
            'success': True,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'train_mae': round(mae_train, 2),
            'test_mae': round(mae_test, 2),
            'train_r2': round(r2_train, 3),
            'test_r2': round(r2_test, 3),
            'baseline_mae': round(baseline_mae, 2),
            'improvement_vs_baseline': round(improvement, 1),
            'features_used': feature_columns,
            'model_type': 'Linear Regression',
            'data_quality': {
                'records_after_cleaning': len(df),
                'loss_mean': round(float(y.mean()), 2),
                'loss_std': round(float(y.std()), 2),
                'loss_min': round(float(y.min()), 2),
                'loss_max': round(float(y.max()), 2)
            },
            'quality_rating': quality
        }

        logger.info(f"\n✓ Model Training Complete!")
        logger.info(f"="*60)
        logger.info(f"  Train MAE: {mae_train:.2f}%")
        logger.info(f"  Test MAE: {mae_test:.2f}%")
        logger.info(f"  Test R²: {r2_test:.3f}")
        logger.info(f"  Baseline MAE: {baseline_mae:.2f}%")
        logger.info(f"  Improvement: {improvement:.1f}%")
        logger.info(f"  Quality: {quality}")
        logger.info(f"="*60)

        return results

    def predict_next_days(self, station_id: int, days_ahead: int = 7) -> List[Dict]:
        if self.model is None:
            self._load_model()
            if self.model is None:
                raise ValueError("No trained model available")

        with self.loss_repo as repo:
            loss_data = repo.get_all(station_id=station_id)[-60:]

        df_clean = self.clean_data(loss_data)
        df = self.prepare_features(df_clean)

        if len(df) == 0:
            raise ValueError("No valid data for predictions")

        latest = df.iloc[-1]

        predictions = []
        last_loss = latest['loss_percentage']

        for day in range(1, days_ahead + 1):
            future_date = datetime.now().date() + timedelta(days=day)

            features = pd.DataFrame([{
                'loss_yesterday': last_loss,
                'loss_7day_avg': latest['loss_7day_avg'],
                'day_of_week': future_date.weekday(),
                'is_weekend': 1 if future_date.weekday() >= 5 else 0,
                'power_factor_7day_avg': latest['power_factor_7day_avg'],
                'consumption_7day_avg': latest['consumption_7day_avg'],
                'consumption_7day_std': latest['consumption_7day_std']
            }])

            predicted_loss = self.model.predict(features)[0]
            last_loss = predicted_loss

            predictions.append({
                'date': future_date.isoformat(),
                'predicted_loss_percentage': round(float(predicted_loss), 2),
                'day_of_week': future_date.strftime('%A')
            })

        return predictions

    def _save_model(self):
        os.makedirs('models', exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)

    def _load_model(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)

    def get_model_info(self) -> Dict:
        if self.model is None:
            self._load_model()

        if self.model is None:
            return {'status': 'No model trained'}

        feature_names = ['loss_yesterday', 'loss_7day_avg', 'day_of_week',
                         'is_weekend', 'power_factor_7day_avg', 'consumption_7day_avg',
                         'consumption_7day_std']

        coefficients = {name: round(float(self.model.coef_[i]), 4)
                        for i, name in enumerate(feature_names)}

        return {
            'status': 'Model ready',
            'model_type': 'Linear Regression',
            'coefficients': coefficients,
            'intercept': round(float(self.model.intercept_), 4)
        }
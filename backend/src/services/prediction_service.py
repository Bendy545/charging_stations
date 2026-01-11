"""
Hourly Loss Prediction Service
===============================
Based on your successful test_predict.py approach!

Uses hourly data + Random Forest for better accuracy.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import pickle
import os

from backend.src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class HourlyPredictionService:
    def __init__(self):
        self.model = None
        self.model_path = "models/hourly_loss_model.pkl"
        self.scaler_path = "models/feature_scaler.pkl"

    def load_hourly_data(self, station_id: Optional[int] = None) -> pd.DataFrame:
        with BaseRepository() as repo:
            query_power = """
                SELECT 
                    timestamp,
                    station_id,
                    active_power_kwh,
                    reactive_power_kwh
                FROM power_consumption
                WHERE 1=1
            """
            if station_id:
                query_power += f" AND station_id = {station_id}"

            df_power = pd.DataFrame(repo.fetchall(query_power))

            query_dist = """
                SELECT 
                    interval_15min as timestamp,
                    station_id,
                    energy_kwh
                FROM distributed_sessions
                WHERE 1=1
            """
            if station_id:
                query_dist += f" AND station_id = {station_id}"

            df_dist = pd.DataFrame(repo.fetchall(query_dist))

        logger.info(f"Loaded {len(df_power)} power records, {len(df_dist)} session records")

        if len(df_power) == 0:
            raise ValueError("No power consumption data found in database")

        if len(df_dist) == 0:
            logger.warning("No distributed session data found - all deliveries will be 0")

        df_power['timestamp'] = pd.to_datetime(df_power['timestamp'])
        df_dist['timestamp'] = pd.to_datetime(df_dist['timestamp']) if len(df_dist) > 0 else pd.Series(dtype='datetime64[ns]')

        df_power['active_power_kwh'] = df_power['active_power_kwh'].astype(float)
        df_power['reactive_power_kwh'] = df_power['reactive_power_kwh'].astype(float)
        df_power['station_id'] = df_power['station_id'].astype(int)

        if len(df_dist) > 0:
            df_dist['energy_kwh'] = df_dist['energy_kwh'].astype(float)
            df_dist['station_id'] = df_dist['station_id'].astype(int)

        df_power_hourly = df_power.set_index('timestamp').groupby('station_id').resample('h').agg({
            'active_power_kwh': 'sum',
            'reactive_power_kwh': 'sum'
        }).reset_index()

        if len(df_dist) > 0:
            df_dist_hourly = df_dist.set_index('timestamp').groupby('station_id').resample('h').agg({
                'energy_kwh': 'sum'
            }).reset_index()
            df_dist_hourly.rename(columns={'energy_kwh': 'delivered_kwh'}, inplace=True)

            df = pd.merge(df_power_hourly, df_dist_hourly,
                          on=['station_id', 'timestamp'], how='left')
        else:
            df = df_power_hourly.copy()
            df['delivered_kwh'] = 0.0

        df['delivered_kwh'] = df['delivered_kwh'].fillna(0)

        df['loss_kwh'] = df['active_power_kwh'] - df['delivered_kwh']

        df_clean = df[
            (df['active_power_kwh'] > 0.1) &
            (df['loss_kwh'] >= 0)
            ].copy()

        df_clean['efficiency'] = (df_clean['delivered_kwh'] /
                                  df_clean['active_power_kwh']) * 100
        df_clean = df_clean[df_clean['efficiency'] <= 100]

        df_clean['hour'] = df_clean['timestamp'].dt.hour
        df_clean['day_of_week'] = df_clean['timestamp'].dt.dayofweek
        df_clean['is_weekend'] = (df_clean['day_of_week'] >= 5).astype(int)

        df_clean['hour_sin'] = np.sin(2 * np.pi * df_clean['hour'] / 24)
        df_clean['hour_cos'] = np.cos(2 * np.pi * df_clean['hour'] / 24)

        numeric_cols = ['active_power_kwh', 'reactive_power_kwh', 'delivered_kwh',
                        'loss_kwh', 'efficiency', 'hour_sin', 'hour_cos']
        for col in numeric_cols:
            df_clean[col] = df_clean[col].astype(float)

        logger.info(f"Cleaned data: {len(df_clean)} hourly records")
        logger.info(f"Average efficiency: {df_clean['efficiency'].mean():.2f}%")

        return df_clean

    def train_model(self, station_id: Optional[int] = None) -> Dict:
        logger.info("="*60)
        logger.info("TRAINING HOURLY PREDICTION MODEL")
        logger.info("="*60)

        df = self.load_hourly_data(station_id)

        if len(df) < 100:
            raise ValueError(f"Not enough data: {len(df)} hours")

        features = [
            'delivered_kwh',
            'reactive_power_kwh',
            'hour',
            'day_of_week',
            'is_weekend',
            'station_id',
            'hour_sin',
            'hour_cos'
        ]

        target = 'loss_kwh'

        X = df[features]
        y = df[target]

        y = y.astype(float)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        logger.info(f"\n📊 Training Data:")
        logger.info(f"  Total samples: {len(df)}")
        logger.info(f"  Train: {len(X_train)}, Test: {len(X_test)}")
        logger.info(f"  Loss range: {y.min():.2f} - {y.max():.2f} kWh")
        logger.info(f"  Loss mean: {y.mean():.2f} kWh")

        self.model = RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            max_depth=20,
            min_samples_split=10,
            n_jobs=-1
        )

        logger.info(f"\n🌲 Training Random Forest...")
        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)

        mae_train = mean_absolute_error(y_train, y_pred_train)
        mae_test = mean_absolute_error(y_test, y_pred_test)
        r2_train = r2_score(y_train, y_pred_train)
        r2_test = r2_score(y_test, y_pred_test)

        feature_importance = dict(zip(features, self.model.feature_importances_))
        feature_importance = {k: round(v, 4) for k, v in
                              sorted(feature_importance.items(),
                                     key=lambda x: x[1], reverse=True)}

        self._save_model()

        if r2_test > 0.6 and mae_test < 2.5:
            quality = "Excellent ⭐⭐⭐"
        elif r2_test > 0.4 and mae_test < 4.0:
            quality = "Good ⭐⭐"
        elif r2_test > 0.2:
            quality = "Fair ⭐"
        else:
            quality = "Poor"

        results = {
            'success': True,
            'model_type': 'Random Forest',
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'train_mae_kwh': round(mae_train, 3),
            'test_mae_kwh': round(mae_test, 3),
            'train_r2': round(r2_train, 4),
            'test_r2': round(r2_test, 4),
            'feature_importance': feature_importance,
            'quality_rating': quality,
            'data_summary': {
                'total_hours': len(df),
                'loss_mean_kwh': round(float(y.mean()), 2),
                'loss_std_kwh': round(float(y.std()), 2),
                'avg_efficiency_pct': round(float(df['efficiency'].mean()), 2)
            }
        }

        logger.info(f"\n✓ Training Complete!")
        logger.info(f"="*60)
        logger.info(f"  Train MAE: {mae_train:.3f} kWh")
        logger.info(f"  Test MAE: {mae_test:.3f} kWh")
        logger.info(f"  Test R²: {r2_test:.4f}")
        logger.info(f"  Quality: {quality}")
        logger.info(f"\n🎯 Top Features:")
        for feat, imp in list(feature_importance.items())[:5]:
            logger.info(f"    {feat}: {imp:.4f}")

        return results

    def predict_next_hours(self, station_id: int, hours_ahead: int = 24) -> List[Dict]:

        if self.model is None:
            self._load_model()
            if self.model is None:
                raise ValueError("No trained model available")

        df = self.load_hourly_data(station_id=station_id)

        if len(df) < 24:
            raise ValueError(f"Need at least 24 hours of data, got {len(df)}")

        recent = df.tail(168)
        avg_delivered = recent['delivered_kwh'].mean()
        avg_reactive = recent['reactive_power_kwh'].mean()

        predictions = []
        now = datetime.now()

        for h in range(1, hours_ahead + 1):
            future_time = now + timedelta(hours=h)

            features = pd.DataFrame([{
                'delivered_kwh': avg_delivered,
                'reactive_power_kwh': avg_reactive,
                'hour': future_time.hour,
                'day_of_week': future_time.weekday(),
                'is_weekend': 1 if future_time.weekday() >= 5 else 0,
                'station_id': station_id,
                'hour_sin': np.sin(2 * np.pi * future_time.hour / 24),
                'hour_cos': np.cos(2 * np.pi * future_time.hour / 24)
            }])

            predicted_loss = self.model.predict(features)[0]

            predictions.append({
                'timestamp': future_time.isoformat(),
                'hour': future_time.hour,
                'predicted_loss_kwh': round(float(predicted_loss), 3),
                'day_of_week': future_time.strftime('%A')
            })

        return predictions

    def predict_daily_summary(self, station_id: int, days_ahead: int = 7) -> List[Dict]:
        hourly_preds = self.predict_next_hours(station_id, hours_ahead=days_ahead * 24)

        daily_summary = []
        hourly_df = pd.DataFrame(hourly_preds)
        hourly_df['date'] = pd.to_datetime(hourly_df['timestamp']).dt.date

        for date, group in hourly_df.groupby('date'):
            daily_summary.append({
                'date': date.isoformat(),
                'predicted_daily_loss_kwh': round(group['predicted_loss_kwh'].sum(), 2),
                'avg_hourly_loss_kwh': round(group['predicted_loss_kwh'].mean(), 2),
                'day_of_week': group.iloc[0]['day_of_week']
            })

        return daily_summary

    def _save_model(self):
        os.makedirs('models', exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        logger.info(f"Model saved to {self.model_path}")

    def _load_model(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            logger.info(f"Model loaded from {self.model_path}")
        else:
            logger.warning("No saved model found")

    def get_model_info(self) -> Dict:
        if self.model is None:
            self._load_model()

        if self.model is None:
            return {'status': 'No model trained'}

        return {
            'status': 'Model ready',
            'model_type': 'Random Forest',
            'n_estimators': self.model.n_estimators,
            'max_depth': self.model.max_depth,
            'n_features': self.model.n_features_in_
        }


if __name__ == "__main__":

    service = HourlyPredictionService()

    print("Training model on hourly data...")
    results = service.train_model(station_id=None)

    print(f"\nResults:")
    print(f"  R² Score: {results['test_r2']}")
    print(f"  MAE: {results['test_mae_kwh']} kWh")
    print(f"  Quality: {results['quality_rating']}")

    print("\nPredicting next 24 hours for Station 3...")
    hourly = service.predict_next_hours(station_id=3, hours_ahead=24)

    print("\nSample predictions:")
    for pred in hourly[:5]:
        print(f"  {pred['timestamp']}: {pred['predicted_loss_kwh']} kWh")

    print("\nPredicting next 7 days (daily summary)...")
    daily = service.predict_daily_summary(station_id=3, days_ahead=7)

    for pred in daily:
        print(f"  {pred['date']}: {pred['predicted_daily_loss_kwh']} kWh total")
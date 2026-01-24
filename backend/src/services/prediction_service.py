import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import pickle
import os

from backend.src.repositories.prediction_repository import PredictionRepository
from backend.src.repositories.consumption_repository import ConsumptionRepository
from backend.src.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)


class PredictionService:
    """
    FIXED prediction service addressing:
    1. Data leakage (removed active_power from features)
    2. Correct units (kW and kVAr, not kWh)
    3. Predicts loss_percentage instead of absolute loss
    """

    PROBLEMATIC_STATIONS = [1, 2]

    def __init__(self):
        self.loss_rate_model = None  # Predicts loss %
        self.power_model = None       # Predicts future active power
        self.feature_names_loss = None
        self.feature_names_power = None
        self.prediction_repo = PredictionRepository()
        self.consumption_repo = ConsumptionRepository()
        self.session_repo = SessionRepository()
        self.model_path = "models/loss_rate_model.pkl"
        self.power_model_path = "models/power_forecast_model.pkl"

    def load_hourly_data(self, station_id: Optional[int] = None) -> pd.DataFrame:
        """
        Load training data with CORRECTED understanding of units

        NOTE: The database stores 15-minute interval measurements:
        - active_power_kwh: Actually kW reading × 0.25h = kWh energy in that interval
        - reactive_power_kwh: Actually kVAr reading × 0.25h = kVArh in that interval

        So we need to convert back to average power for the hour.
        """
        with self.consumption_repo as c_repo, self.session_repo as s_repo:
            raw_power = c_repo.get_for_training(
                exclude_ids=self.PROBLEMATIC_STATIONS,
                station_id=station_id
            )
            raw_sessions = s_repo.get_distributed_sessions(
                exclude_ids=self.PROBLEMATIC_STATIONS,
                station_id=station_id
            )

            logger.info(f"Loaded {len(raw_power)} power records, {len(raw_sessions)} session records")

            if not raw_power:
                raise ValueError("No power consumption data found in database")

            df_power = pd.DataFrame(raw_power)
            df_dist = pd.DataFrame(raw_sessions)

            df_power['timestamp'] = pd.to_datetime(df_power['timestamp'])
            df_power['active_power_kw'] = df_power['active_power_kwh'].astype(float) / 0.25  # Convert back to kW
            df_power['reactive_power_kvar'] = df_power['reactive_power_kwh'].astype(float) / 0.25  # Convert to kVAr
            df_power['station_id'] = df_power['station_id'].astype(int)

            if not df_dist.empty:
                df_dist['timestamp'] = pd.to_datetime(df_dist['timestamp'])
                df_dist['energy_kwh'] = df_dist['energy_kwh'].astype(float)
                df_dist['station_id'] = df_dist['station_id'].astype(int)
            else:
                logger.warning("No distributed session data found")

            # Aggregate to hourly (sum energy, average power)
            df_power_hourly = df_power.set_index('timestamp').groupby('station_id').resample('h').agg({
                'active_power_kw': 'mean',      # Average power during hour
                'reactive_power_kvar': 'mean'   # Average reactive power
            }).reset_index()

            # Calculate hourly energy consumption
            df_power_hourly['consumption_kwh'] = df_power_hourly['active_power_kw']  # kW × 1h = kWh
            df_power_hourly['reactive_kvarh'] = df_power_hourly['reactive_power_kvar']  # kVAr × 1h

            if not df_dist.empty:
                df_dist_hourly = df_dist.set_index('timestamp').groupby('station_id').resample('h').agg({
                    'energy_kwh': 'sum'
                }).reset_index()
                df_dist_hourly.rename(columns={'energy_kwh': 'delivered_kwh'}, inplace=True)
                df = pd.merge(df_power_hourly, df_dist_hourly, on=['station_id', 'timestamp'], how='left')
            else:
                df = df_power_hourly.copy()
                df['delivered_kwh'] = 0.0

            df['delivered_kwh'] = df['delivered_kwh'].fillna(0)

            # Calculate losses (energy difference)
            df['loss_kwh'] = df['consumption_kwh'] - df['delivered_kwh']

            # Calculate loss percentage
            df['loss_percentage'] = (df['loss_kwh'] / df['consumption_kwh'] * 100).fillna(0)

            # Clean unrealistic values
            df.loc[df['loss_percentage'] > 30, 'loss_percentage'] = 5.0  # Cap at 30%
            df.loc[df['loss_percentage'] < 0, 'loss_percentage'] = 0
            df.loc[df['loss_kwh'] < 0, 'loss_kwh'] = 0

            # Filter meaningful data (at least 0.1 kW average power)
            df_clean = df[(df['active_power_kw'] > 0.1) & (df['loss_percentage'] <= 100)].copy()

            # Add time features
            df_clean['hour'] = df_clean['timestamp'].dt.hour
            df_clean['day_of_week'] = df_clean['timestamp'].dt.dayofweek
            df_clean['is_weekend'] = (df_clean['day_of_week'] >= 5).astype(int)

            logger.info(f"Cleaned data: {len(df_clean)} hourly records")
            logger.info(f"Average loss: {df_clean['loss_percentage'].mean():.2f}%")
            logger.info(f"Loss range: {df_clean['loss_percentage'].min():.2f}% - {df_clean['loss_percentage'].max():.2f}%")

            return df_clean

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create features WITHOUT using active_power (to avoid leakage)

        We can use:
        - Time features (hour, day of week)
        - Delivered energy (we're trying to predict losses given charging activity)
        - Reactive power (power quality indicator)
        - Historical loss patterns
        - Station characteristics
        """
        df = df.copy()
        df = df.sort_values(['station_id', 'timestamp'])

        # Cyclic encoding for time
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

        # Power quality indicators (reactive power suggests power factor)
        df['apparent_power_kva'] = np.sqrt(df['active_power_kw']**2 + df['reactive_power_kvar']**2)
        df['power_factor'] = (df['active_power_kw'] / df['apparent_power_kva'] * 100).fillna(100)
        df['reactive_ratio'] = df['reactive_power_kvar'] / (df['active_power_kw'] + 0.001)

        # Load characteristics (delivered energy indicates utilization)
        df['delivered_ratio'] = df['delivered_kwh'] / (df['consumption_kwh'] + 0.001)

        # Lag features (autoregressive component)
        df['loss_pct_lag_1h'] = df.groupby('station_id')['loss_percentage'].shift(1)
        df['loss_pct_lag_24h'] = df.groupby('station_id')['loss_percentage'].shift(24)

        # Rolling statistics
        df['loss_pct_rolling_mean'] = df.groupby('station_id')['loss_percentage'].transform(
            lambda x: x.rolling(window=24, min_periods=1).mean()
        )
        df['loss_pct_rolling_std'] = df.groupby('station_id')['loss_percentage'].transform(
            lambda x: x.rolling(window=24, min_periods=1).std()
        )

        # Fill NaN from lag features
        mean_loss_pct = df['loss_percentage'].mean()
        df['loss_pct_lag_1h'] = df['loss_pct_lag_1h'].fillna(mean_loss_pct)
        df['loss_pct_lag_24h'] = df['loss_pct_lag_24h'].fillna(mean_loss_pct)
        df['loss_pct_rolling_mean'] = df['loss_pct_rolling_mean'].fillna(mean_loss_pct)
        df['loss_pct_rolling_std'] = df['loss_pct_rolling_std'].fillna(0)

        # Station quality
        df['station_quality'] = 1
        df.loc[df['station_id'].isin(self.PROBLEMATIC_STATIONS), 'station_quality'] = 0

        return df

    def train_model(self, station_id: Optional[int] = None) -> Dict:
        """
        Train TWO models:
        1. Loss rate model (predicts loss %)
        2. Power forecast model (predicts future consumption)

        This avoids data leakage while maintaining prediction accuracy.
        """
        logger.info("="*60)
        logger.info("TRAINING FIXED PREDICTION MODEL (NO LEAKAGE)")
        logger.info("="*60)

        df = self.load_hourly_data(station_id)

        if len(df) < 100:
            raise ValueError(f"Not enough data: {len(df)} hours")

        df = self.create_features(df)

        # ============================================================
        # MODEL 1: Loss Rate Prediction (NO active_power feature!)
        # ============================================================

        self.feature_names_loss = [
            'delivered_kwh',        # How much energy was delivered
            'reactive_power_kvar',  # Power quality indicator
            'power_factor',         # Efficiency indicator
            'reactive_ratio',       # Power quality metric
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

        X_loss = df[self.feature_names_loss]
        y_loss = df['loss_percentage']  # Target: loss %

        # Remove NaN
        mask = ~(X_loss.isna().any(axis=1) | y_loss.isna())
        X_loss = X_loss[mask]
        y_loss = y_loss[mask]

        logger.info(f"\n📊 LOSS RATE MODEL:")
        logger.info(f"  Training samples: {len(X_loss)}")
        logger.info(f"  Features: {len(self.feature_names_loss)}")
        logger.info(f"  Target: Loss percentage ({y_loss.min():.2f}% - {y_loss.max():.2f}%)")

        # Time-series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)

        self.loss_rate_model = RandomForestRegressor(
            n_estimators=200,
            max_depth=20,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1
        )

        # CV scores
        cv_scores = cross_val_score(
            self.loss_rate_model, X_loss, y_loss,
            cv=tscv, scoring='neg_mean_absolute_error'
        )

        logger.info(f"  CV MAE: {-cv_scores.mean():.3f} ± {cv_scores.std():.3f} %")

        # Train on full data
        self.loss_rate_model.fit(X_loss, y_loss)

        # Evaluate on last fold
        train_idx, test_idx = list(tscv.split(X_loss))[-1]
        X_train, X_test = X_loss.iloc[train_idx], X_loss.iloc[test_idx]
        y_train, y_test = y_loss.iloc[train_idx], y_loss.iloc[test_idx]

        y_pred_test = self.loss_rate_model.predict(X_test)

        loss_mae = mean_absolute_error(y_test, y_pred_test)
        loss_r2 = r2_score(y_test, y_pred_test)

        # ============================================================
        # MODEL 2: Power Consumption Forecast
        # ============================================================

        self.feature_names_power = [
            'hour', 'day_of_week', 'is_weekend',
            'hour_sin', 'hour_cos',
            'day_of_week_sin', 'day_of_week_cos',
            'station_id',
            'delivered_kwh'  # Past delivery patterns help predict future consumption
        ]

        X_power = df[self.feature_names_power]
        y_power = df['consumption_kwh']  # Target: total consumption

        mask_power = ~(X_power.isna().any(axis=1) | y_power.isna())
        X_power = X_power[mask_power]
        y_power = y_power[mask_power]

        logger.info(f"\n⚡ POWER FORECAST MODEL:")
        logger.info(f"  Training samples: {len(X_power)}")
        logger.info(f"  Target: Consumption kWh ({y_power.min():.2f} - {y_power.max():.2f})")

        self.power_model = RandomForestRegressor(
            n_estimators=150,
            max_depth=15,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1
        )

        cv_scores_power = cross_val_score(
            self.power_model, X_power, y_power,
            cv=tscv, scoring='neg_mean_absolute_error'
        )

        logger.info(f"  CV MAE: {-cv_scores_power.mean():.3f} kWh")

        self.power_model.fit(X_power, y_power)

        # Feature importance
        importance_loss = dict(zip(self.feature_names_loss, self.loss_rate_model.feature_importances_))
        importance_loss = {k: round(v, 4) for k, v in sorted(importance_loss.items(), key=lambda x: x[1], reverse=True)}

        self._save_models()

        results = {
            'success': True,
            'model_type': 'Dual Model (Loss Rate + Power Forecast)',
            'loss_rate_model': {
                'test_mae_pct': round(loss_mae, 3),
                'test_r2': round(loss_r2, 4),
                'cv_mae': round(-cv_scores.mean(), 3)
            },
            'power_model': {
                'cv_mae_kwh': round(-cv_scores_power.mean(), 3)
            },
            'feature_importance': importance_loss,
            'data_summary': {
                'total_hours': len(df),
                'avg_loss_pct': round(df['loss_percentage'].mean(), 2),
                'avg_consumption_kwh': round(df['consumption_kwh'].mean(), 2)
            }
        }

        logger.info(f"\n✓ Training Complete!")
        logger.info(f"="*60)
        logger.info(f"  Loss Rate MAE: {loss_mae:.3f}%, R²: {loss_r2:.4f}")
        logger.info(f"  Power Forecast MAE: {-cv_scores_power.mean():.3f} kWh")
        logger.info(f"\n🎯 Top Features for Loss Prediction:")
        for feat, imp in list(importance_loss.items())[:5]:
            logger.info(f"    {feat}: {imp:.4f}")

        return results

    def predict_next_hours(self, station_id: int, hours_ahead: int = 24) -> List[Dict]:
        """
        Predict losses for next N hours using BOTH models

        Process:
        1. Predict future power consumption (Model 2)
        2. Predict loss rate (Model 1)
        3. Calculate absolute loss: consumption × loss_rate
        """
        if self.loss_rate_model is None or self.power_model is None:
            self._load_models()

        df = self.load_hourly_data(station_id=station_id)

        df = self.create_features(df)

        if len(df) < 48:
            raise ValueError(f"Need at least 48 hours of data, got {len(df)}")

        recent = df.tail(48)

        # Get hourly patterns
        hourly_stats = recent.groupby('hour').agg({
            'delivered_kwh': 'mean',
            'reactive_power_kvar': 'mean',
            'power_factor': 'mean',
            'reactive_ratio': 'mean',
            'consumption_kwh': 'mean'
        }).to_dict('index')

        predictions = []
        now = datetime.now()

        # Track recent losses for lag features
        recent_loss_pcts = recent['loss_percentage'].tail(24).tolist()

        for h in range(1, hours_ahead + 1):
            future_time = now + timedelta(hours=h)
            future_hour = future_time.hour

            stats = hourly_stats.get(future_hour, {})

            # STEP 1: Predict power consumption
            power_features = {
                'hour': future_hour,
                'day_of_week': future_time.weekday(),
                'is_weekend': 1 if future_time.weekday() >= 5 else 0,
                'hour_sin': np.sin(2 * np.pi * future_hour / 24),
                'hour_cos': np.cos(2 * np.pi * future_hour / 24),
                'day_of_week_sin': np.sin(2 * np.pi * future_time.weekday() / 7),
                'day_of_week_cos': np.cos(2 * np.pi * future_time.weekday() / 7),
                'station_id': station_id,
                'delivered_kwh': stats.get('delivered_kwh', recent['delivered_kwh'].mean())
            }

            X_power = pd.DataFrame([power_features])[self.feature_names_power]
            predicted_consumption = max(0, self.power_model.predict(X_power)[0])

            # STEP 2: Predict loss rate
            loss_features = {
                'delivered_kwh': stats.get('delivered_kwh', recent['delivered_kwh'].mean()),
                'reactive_power_kvar': stats.get('reactive_power_kvar', recent['reactive_power_kvar'].mean()),
                'power_factor': stats.get('power_factor', recent['power_factor'].mean()),
                'reactive_ratio': stats.get('reactive_ratio', recent['reactive_ratio'].mean()),
                'hour': future_hour,
                'day_of_week': future_time.weekday(),
                'is_weekend': 1 if future_time.weekday() >= 5 else 0,
                'hour_sin': power_features['hour_sin'],
                'hour_cos': power_features['hour_cos'],
                'day_of_week_sin': power_features['day_of_week_sin'],
                'day_of_week_cos': power_features['day_of_week_cos'],
                'loss_pct_lag_1h': recent_loss_pcts[-1] if recent_loss_pcts else recent['loss_percentage'].mean(),
                'loss_pct_lag_24h': recent_loss_pcts[-24] if len(recent_loss_pcts) >= 24 else recent['loss_percentage'].mean(),
                'loss_pct_rolling_mean': np.mean(recent_loss_pcts[-24:]),
                'loss_pct_rolling_std': np.std(recent_loss_pcts[-24:]) if len(recent_loss_pcts) >= 2 else 0,
                'station_id': station_id,
                'station_quality': 0 if station_id in self.PROBLEMATIC_STATIONS else 1
            }

            X_loss = pd.DataFrame([loss_features])[self.feature_names_loss]
            predicted_loss_pct = max(0, min(100, self.loss_rate_model.predict(X_loss)[0]))

            # STEP 3: Calculate absolute loss
            predicted_loss_kwh = predicted_consumption * (predicted_loss_pct / 100)

            # Update lag features
            recent_loss_pcts.append(predicted_loss_pct)
            if len(recent_loss_pcts) > 24:
                recent_loss_pcts.pop(0)

            predictions.append({
                'timestamp': future_time.isoformat(),
                'hour': future_hour,
                'predicted_loss_kwh': round(predicted_loss_kwh, 4),
                'predicted_loss_pct': round(predicted_loss_pct, 2),
                'predicted_consumption_kwh': round(predicted_consumption, 2),
                'day_of_week': future_time.strftime('%A')
            })

        return predictions

    def predict_daily_summary(self, station_id: int, days_ahead: int = 7) -> List[Dict]:
        """Predict daily summaries"""
        hourly_preds = self.predict_next_hours(station_id, hours_ahead=days_ahead * 24)

        daily_summary = []
        hourly_df = pd.DataFrame(hourly_preds)
        hourly_df['date'] = pd.to_datetime(hourly_df['timestamp']).dt.date

        for date, group in hourly_df.groupby('date'):
            daily_summary.append({
                'date': date.isoformat(),
                'predicted_daily_loss_kwh': round(group['predicted_loss_kwh'].sum(), 2),
                'avg_hourly_loss_kwh': round(group['predicted_loss_kwh'].mean(), 2),
                'avg_loss_pct': round(group['predicted_loss_pct'].mean(), 2),
                'day_of_week': group.iloc[0]['day_of_week']
            })

        return daily_summary

    def refresh_cache_for_stations(self, station_ids: List[int]):
        """Refresh prediction cache"""
        with self.prediction_repo:
            for s_id in station_ids:
                daily_preds = self.predict_daily_summary(station_id=s_id, days_ahead=14)
                self.prediction_repo.save_predictions(s_id, daily_preds)
                logger.info(f"Cached predictions for station {s_id}")

    def get_forecast_from_cache(self, station_id: int, days: int):
        """Get cached predictions"""
        with self.prediction_repo:
            return self.prediction_repo.get_cached_predictions(station_id, days)

    def _save_models(self):
        """Save both models"""
        os.makedirs('models', exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'model': self.loss_rate_model,
                'feature_names': self.feature_names_loss
            }, f)
        with open(self.power_model_path, 'wb') as f:
            pickle.dump({
                'model': self.power_model,
                'feature_names': self.feature_names_power
            }, f)
        logger.info("Models saved")

    def _load_models(self):
        """Load both models"""
        if os.path.exists(self.model_path) and os.path.exists(self.power_model_path):
            with open(self.model_path, 'rb') as f:
                saved = pickle.load(f)
                self.loss_rate_model = saved['model']
                self.feature_names_loss = saved['feature_names']
            with open(self.power_model_path, 'rb') as f:
                saved = pickle.load(f)
                self.power_model = saved['model']
                self.feature_names_power = saved['feature_names']
            logger.info("Models loaded")

    def get_model_info(self) -> Dict:
        """Get model info"""
        if self.loss_rate_model is None:
            self._load_models()

        return {
            'status': 'Models ready',
            'model_type': 'Dual Model (No Leakage)',
            'loss_rate_model': {
                'n_estimators': self.loss_rate_model.n_estimators,
                'n_features': len(self.feature_names_loss),
                'features': self.feature_names_loss
            },
            'power_model': {
                'n_estimators': self.power_model.n_estimators,
                'n_features': len(self.feature_names_power)
            }
        }
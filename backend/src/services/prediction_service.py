import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from backend.src.repositories.prediction_repository import PredictionRepository
from backend.src.repositories.consumption_repository import ConsumptionRepository
from backend.src.repositories.session_repository import SessionRepository
from backend.src.services.models.loss_rate_model import LossRateModel
from backend.src.services.models.power_forecast_model import PowerForecastModel

logger = logging.getLogger(__name__)


class PredictionService:
    """
    Orchestrates the two prediction models:

    1. PowerForecastModel  — predicts how much energy a station will consume
    2. LossRateModel       — predicts what percentage of that consumption is lost

    Final prediction: predicted_loss_kwh = consumption × (loss_rate / 100)

    Training data is fenced to the valid session date range to prevent
    corruption from periods without session data.
    """

    PROBLEMATIC_STATIONS = [1, 2]
    SESSION_DATA_START = datetime(2025, 3, 16)
    SESSION_DATA_END = datetime(2025, 11, 30)

    def __init__(self):
        self.loss_model = LossRateModel()
        self.power_model = PowerForecastModel()

        self.prediction_repo = PredictionRepository()
        self.consumption_repo = ConsumptionRepository()
        self.session_repo = SessionRepository()

    def load_hourly_data(self, station_id: Optional[int] = None) -> pd.DataFrame:
        """
        Load and prepare training data from the database.

        Merges power consumption with distributed charging sessions,
        computes hourly aggregates, and calculates loss metrics.

        Data is fenced to SESSION_DATA_START..SESSION_DATA_END to avoid
        training on periods without session data (which would appear as
        100% loss and corrupt the model).

        Units note:
            Database stores 15-min interval energy (kWh = kW × 0.25h).
            We convert back to average power (kW) then aggregate hourly.
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
        df_power['timestamp'] = pd.to_datetime(df_power['timestamp'])
        df_power['active_power_kw'] = df_power['active_power_kwh'].astype(float) / 0.25
        df_power['reactive_power_kvar'] = df_power['reactive_power_kwh'].astype(float) / 0.25
        df_power['station_id'] = df_power['station_id'].astype(int)

        before = len(df_power)
        df_power = df_power[
            (df_power['timestamp'] >= self.SESSION_DATA_START) &
            (df_power['timestamp'] <= self.SESSION_DATA_END)
            ]
        if before != len(df_power):
            logger.info(
                f"Date fence: {before} -> {len(df_power)} records "
                f"({self.SESSION_DATA_START.date()} to {self.SESSION_DATA_END.date()})"
            )

        if df_power.empty:
            raise ValueError(
                f"No power data within session range "
                f"({self.SESSION_DATA_START.date()} - {self.SESSION_DATA_END.date()})"
            )

        df_dist = pd.DataFrame(raw_sessions)
        if not df_dist.empty:
            df_dist['timestamp'] = pd.to_datetime(df_dist['timestamp'])
            df_dist['energy_kwh'] = df_dist['energy_kwh'].astype(float)
            df_dist['station_id'] = df_dist['station_id'].astype(int)
            df_dist = df_dist[
                (df_dist['timestamp'] >= self.SESSION_DATA_START) &
                (df_dist['timestamp'] <= self.SESSION_DATA_END)
                ]
        else:
            logger.warning("No distributed session data found")

        df_hourly = (
            df_power
            .set_index('timestamp')
            .groupby('station_id')
            .resample('h')
            .agg({
                'active_power_kw': 'mean',
                'reactive_power_kvar': 'mean'
            })
            .reset_index()
        )
        df_hourly['consumption_kwh'] = df_hourly['active_power_kw']       # kW × 1h = kWh
        df_hourly['reactive_kvarh'] = df_hourly['reactive_power_kvar']    # kVAr × 1h

        if not df_dist.empty:
            df_dist_hourly = (
                df_dist
                .set_index('timestamp')
                .groupby('station_id')
                .resample('h')
                .agg({'energy_kwh': 'sum'})
                .reset_index()
                .rename(columns={'energy_kwh': 'delivered_kwh'})
            )
            df = pd.merge(df_hourly, df_dist_hourly, on=['station_id', 'timestamp'], how='left')
        else:
            df = df_hourly.copy()
            df['delivered_kwh'] = 0.0

        df['delivered_kwh'] = df['delivered_kwh'].fillna(0)

        df['loss_kwh'] = df['consumption_kwh'] - df['delivered_kwh']
        df['loss_percentage'] = (df['loss_kwh'] / df['consumption_kwh'] * 100).fillna(0)

        df.loc[df['loss_percentage'] > 30, 'loss_percentage'] = 5.0
        df.loc[df['loss_percentage'] < 0, 'loss_percentage'] = 0
        df.loc[df['loss_kwh'] < 0, 'loss_kwh'] = 0

        df = df[(df['active_power_kw'] > 0.1) & (df['loss_percentage'] <= 100)].copy()

        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

        logger.info(f"Training data ready: {len(df)} hourly records")
        logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        logger.info(f"Average loss: {df['loss_percentage'].mean():.2f}%")

        return df

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer features for both models.

        Creates:
        - Cyclical time encodings (sin/cos for hour and day)
        - Power quality metrics (power factor, reactive ratio)
        - Lag features (loss % at t-1h and t-24h)
        - Rolling statistics (24h mean and std of loss %)
        - Station quality flag
        """
        df = df.copy()
        df = df.sort_values(['station_id', 'timestamp'])

        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

        df['apparent_power_kva'] = np.sqrt(df['active_power_kw'] ** 2 + df['reactive_power_kvar'] ** 2)
        df['power_factor'] = (df['active_power_kw'] / df['apparent_power_kva'] * 100).fillna(100)
        df['reactive_ratio'] = df['reactive_power_kvar'] / (df['active_power_kw'] + 0.001)

        df['delivered_ratio'] = df['delivered_kwh'] / (df['consumption_kwh'] + 0.001)

        df['loss_pct_lag_1h'] = df.groupby('station_id')['loss_percentage'].shift(1)
        df['loss_pct_lag_24h'] = df.groupby('station_id')['loss_percentage'].shift(24)

        df['loss_pct_rolling_mean'] = df.groupby('station_id')['loss_percentage'].transform(
            lambda x: x.rolling(window=24, min_periods=1).mean()
        )
        df['loss_pct_rolling_std'] = df.groupby('station_id')['loss_percentage'].transform(
            lambda x: x.rolling(window=24, min_periods=1).std()
        )

        mean_loss = df['loss_percentage'].mean()
        df['loss_pct_lag_1h'] = df['loss_pct_lag_1h'].fillna(mean_loss)
        df['loss_pct_lag_24h'] = df['loss_pct_lag_24h'].fillna(mean_loss)
        df['loss_pct_rolling_mean'] = df['loss_pct_rolling_mean'].fillna(mean_loss)
        df['loss_pct_rolling_std'] = df['loss_pct_rolling_std'].fillna(0)

        df['station_quality'] = 1
        df.loc[df['station_id'].isin(self.PROBLEMATIC_STATIONS), 'station_quality'] = 0

        return df

    def train_model(self, station_id: Optional[int] = None) -> Dict:
        """
        Train both models on historical data.

        Steps:
        1. Load and merge consumption + session data
        2. Engineer features
        3. Train PowerForecastModel (predicts consumption)
        4. Train LossRateModel (predicts loss %)
        5. Save both models to disk

        Returns:
            Combined training results with metrics for both models
        """
        logger.info("=" * 60)
        logger.info("TRAINING PREDICTION MODELS")
        logger.info(f"Data range: {self.SESSION_DATA_START.date()} to {self.SESSION_DATA_END.date()}")
        logger.info("=" * 60)

        df = self.load_hourly_data(station_id)

        if len(df) < 100:
            raise ValueError(f"Not enough data: {len(df)} hours (need at least 100)")

        df = self.create_features(df)

        power_results = self.power_model.train(df)
        loss_results = self.loss_model.train(df)

        self.power_model.save()
        self.loss_model.save()

        logger.info("=" * 60)
        logger.info("✓ Training complete!")
        logger.info(f"  Loss Rate MAE: {loss_results['cv_mae']:.3f}%")
        logger.info(f"  Power Forecast MAE: {power_results['cv_mae_kwh']:.3f} kWh")
        logger.info("=" * 60)

        return {
            'success': True,
            'model_type': 'Dual Model (Loss Rate + Power Forecast)',
            'training_date_range': {
                'start': self.SESSION_DATA_START.date().isoformat(),
                'end': self.SESSION_DATA_END.date().isoformat()
            },
            'loss_rate_model': loss_results,
            'power_model': power_results,
            'data_summary': {
                'total_hours': len(df),
                'avg_loss_pct': round(df['loss_percentage'].mean(), 2),
                'avg_consumption_kwh': round(df['consumption_kwh'].mean(), 2)
            }
        }

    def _ensure_models_loaded(self):
        """Load models from disk if not already in memory"""
        if not self.loss_model.is_ready or not self.power_model.is_ready:
            if not self.loss_model.load() or not self.power_model.load():
                raise RuntimeError("Models not found. Train first via POST /api/predictions/train")

    def predict_next_hours(self, station_id: int, hours_ahead: int = 24) -> List[Dict]:
        """
        Predict losses for the next N hours.

        Process for each future hour:
        1. PowerForecastModel predicts consumption (kWh)
        2. LossRateModel predicts loss rate (%)
        3. Absolute loss = consumption × (loss_rate / 100)

        Lag features are updated with each prediction to maintain
        autoregressive consistency.
        """
        self._ensure_models_loaded()

        df = self.load_hourly_data(station_id=station_id)
        df = self.create_features(df)

        if len(df) < 48:
            raise ValueError(f"Need at least 48 hours of data, got {len(df)}")

        recent = df.tail(48)

        hourly_stats = recent.groupby('hour').agg({
            'delivered_kwh': 'mean',
            'reactive_power_kvar': 'mean',
            'power_factor': 'mean',
            'reactive_ratio': 'mean',
            'consumption_kwh': 'mean'
        }).to_dict('index')

        recent_loss_pcts = recent['loss_percentage'].tail(24).tolist()

        predictions = []
        now = datetime.now()

        for h in range(1, hours_ahead + 1):
            future_time = now + timedelta(hours=h)
            future_hour = future_time.hour
            stats = hourly_stats.get(future_hour, {})

            time_features = {
                'hour': future_hour,
                'day_of_week': future_time.weekday(),
                'is_weekend': 1 if future_time.weekday() >= 5 else 0,
                'hour_sin': np.sin(2 * np.pi * future_hour / 24),
                'hour_cos': np.cos(2 * np.pi * future_hour / 24),
                'day_of_week_sin': np.sin(2 * np.pi * future_time.weekday() / 7),
                'day_of_week_cos': np.cos(2 * np.pi * future_time.weekday() / 7),
            }

            avg_delivered = stats.get('delivered_kwh', recent['delivered_kwh'].mean())

            power_features = {
                **time_features,
                'station_id': station_id,
                'delivered_kwh': avg_delivered
            }
            predicted_consumption = self.power_model.predict(
                pd.DataFrame([power_features])
            )

            loss_features = {
                **time_features,
                'delivered_kwh': avg_delivered,
                'reactive_power_kvar': stats.get('reactive_power_kvar', recent['reactive_power_kvar'].mean()),
                'power_factor': stats.get('power_factor', recent['power_factor'].mean()),
                'reactive_ratio': stats.get('reactive_ratio', recent['reactive_ratio'].mean()),
                'loss_pct_lag_1h': recent_loss_pcts[-1] if recent_loss_pcts else recent['loss_percentage'].mean(),
                'loss_pct_lag_24h': recent_loss_pcts[-24] if len(recent_loss_pcts) >= 24 else recent['loss_percentage'].mean(),
                'loss_pct_rolling_mean': np.mean(recent_loss_pcts[-24:]),
                'loss_pct_rolling_std': np.std(recent_loss_pcts[-24:]) if len(recent_loss_pcts) >= 2 else 0,
                'station_id': station_id,
                'station_quality': 0 if station_id in self.PROBLEMATIC_STATIONS else 1
            }
            predicted_loss_pct = self.loss_model.predict(
                pd.DataFrame([loss_features])
            )

            predicted_loss_kwh = predicted_consumption * (predicted_loss_pct / 100)

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
        """Aggregate hourly predictions into daily summaries"""
        hourly_preds = self.predict_next_hours(station_id, hours_ahead=days_ahead * 24)

        hourly_df = pd.DataFrame(hourly_preds)
        hourly_df['date'] = pd.to_datetime(hourly_df['timestamp']).dt.date

        daily_summary = []
        for date_val, group in hourly_df.groupby('date'):
            daily_summary.append({
                'date': date_val.isoformat(),
                'predicted_daily_loss_kwh': round(group['predicted_loss_kwh'].sum(), 2),
                'avg_hourly_loss_kwh': round(group['predicted_loss_kwh'].mean(), 2),
                'avg_loss_pct': round(group['predicted_loss_pct'].mean(), 2),
                'day_of_week': group.iloc[0]['day_of_week']
            })

        return daily_summary


    def refresh_cache_for_stations(self, station_ids: List[int]):
        """Generate and cache 14-day forecasts for given stations"""
        with self.prediction_repo:
            for s_id in station_ids:
                daily_preds = self.predict_daily_summary(station_id=s_id, days_ahead=14)
                self.prediction_repo.save_predictions(s_id, daily_preds)
                logger.info(f"Cached 14-day forecast for station {s_id}")

    def get_forecast_from_cache(self, station_id: int, days: int):
        """Retrieve cached predictions from database"""
        with self.prediction_repo:
            return self.prediction_repo.get_cached_predictions(station_id, days)

    def get_model_info(self) -> Dict:
        """Get status and metadata for both models"""
        self._ensure_models_loaded()
        return {
            'status': 'Models ready',
            'model_type': 'Dual Model (Loss Rate + Power Forecast)',
            'training_date_range': {
                'start': self.SESSION_DATA_START.date().isoformat(),
                'end': self.SESSION_DATA_END.date().isoformat()
            },
            'loss_rate_model': self.loss_model.get_info(),
            'power_model': self.power_model.get_info()
        }
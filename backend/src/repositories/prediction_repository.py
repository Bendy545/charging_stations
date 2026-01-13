from typing import List, Dict
from backend.src.repositories.base import BaseRepository

class PredictionRepository(BaseRepository):
    def save_predictions(self, station_id: int, predictions: List[Dict]):
        query = """
            INSERT INTO prediction_cache (station_id, prediction_date, predicted_loss_kwh)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                predicted_loss_kwh = VALUES(predicted_loss_kwh),
                predicted_at = CURRENT_TIMESTAMP
        """
        for p in predictions:
            date_only = p['date'][:10] if isinstance(p['date'], str) else p['date']

            self.execute(query, (station_id, date_only, p['predicted_daily_loss_kwh']))

    def get_cached_predictions(self, station_id: int, days: int) -> List[Dict]:
        query = """
            SELECT 
                prediction_date as date, -- MUSÍ se jmenovat 'date'
                predicted_loss_kwh as predicted_daily_loss_kwh, -- MUSÍ se jmenovat takto
                0.0 as avg_hourly_loss_kwh, 
                'Day' as day_of_week
            FROM prediction_cache 
            WHERE station_id = %s AND prediction_date >= CURRENT_DATE
            ORDER BY prediction_date ASC
            LIMIT %s
            """
        return self.fetchall(query, (station_id, days))
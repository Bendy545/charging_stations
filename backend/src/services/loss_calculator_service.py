from typing import List, Optional
from datetime import date
from backend.src.repositories.loss_repository import LossRepository
import logging

logger = logging.getLogger(__name__)

class LossCalculatorService:
    def __init__(self):
        self.loss_repo = LossRepository()

    def recalculate_all(self) -> dict:
        """Kompletní přepočet - volá metody v repository"""
        with self.loss_repo as repo:
            # Všechna logika z proper_loss_calculator je teď v metodách repo
            repo.ensure_tables_exist()
            repo.run_energy_distribution()
            repo.calculate_losses_with_distribution()

            stats = repo.get_statistics()
            return {
                "total_records": stats['total_records'],
                "average_loss_percentage": round(float(stats['avg_loss_pct']), 2) if stats['avg_loss_pct'] else 0
            }

    def get_losses(self, station_id=None, start_date=None, end_date=None):
        with self.loss_repo as repo:
            return repo.get_all(station_id, start_date, end_date)

    def get_statistics(self, station_id=None, exclude_problematic=True):
        with self.loss_repo as repo:
            return repo.get_statistics(station_id)
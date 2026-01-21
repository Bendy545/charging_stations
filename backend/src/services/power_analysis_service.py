from typing import Optional
from backend.src.repositories.loss_repository import LossRepository
import logging

logger = logging.getLogger(__name__)

class PowerAnalysisService:
    """Service for power quality and power factor analysis"""

    def __init__(self):
        self.loss_repo = LossRepository()

    def get_power_factor_analysis(
            self,
            station_id: Optional[int] = None
    ) -> dict:
        """
        Calculate power factor analysis for stations.
        Only considers intervals with meaningful active power.

        Returns:
            Dictionary with power factor metrics
        """
        with self.loss_repo:
            losses = self.loss_repo.get_all(station_id=station_id)

            if not losses:
                return None

            ACTIVE_THRESHOLD_KWH = 0.5

            active_losses = [l for l in losses if l.total_consumption_kwh >= ACTIVE_THRESHOLD_KWH]

            if not active_losses:
                return {
                    "power_factor": 0.0,
                    "status": "no_data",
                    "message": "No active charging periods found",
                    "total_active": 0.0,
                    "total_reactive": 0.0,
                    "apparent_power": 0.0
                }

            total_active = sum(l.total_consumption_kwh for l in active_losses)
            total_reactive = sum(abs(l.total_reactive_kwh) for l in active_losses)

            if total_active > 0 and total_reactive / total_active > 1.5:
                logger.warning(
                    f"Station {station_id}: Reactive power ({total_reactive:.2f}) "
                    f"is {total_reactive/total_active:.1f}x active power ({total_active:.2f}). "
                    f"Check meter configuration."
                )

            if total_reactive == 0:
                return {
                    "power_factor": 100.0,
                    "status": "excellent",
                    "total_active": round(total_active, 2),
                    "total_reactive": 0.0,
                    "apparent_power": round(total_active, 2),
                    "periods_analyzed": len(active_losses),
                    "periods_filtered": len(losses) - len(active_losses)
                }

            apparent = (total_active**2 + total_reactive**2)**0.5
            power_factor = (total_active / apparent * 100) if apparent > 0 else 100.0

            if power_factor >= 95:
                status = "excellent"
            elif power_factor >= 85:
                status = "good"
            elif power_factor >= 70:
                status = "fair"
            else:
                status = "poor"

            return {
                "power_factor": round(power_factor, 1),
                "status": status,
                "total_active": round(total_active, 2),
                "total_reactive": round(total_reactive, 2),
                "apparent_power": round(apparent, 2),
                "reactive_losses_estimate": round(total_reactive * 0.03, 2),
                "periods_analyzed": len(active_losses),
                "periods_filtered": len(losses) - len(active_losses)
            }

    def get_power_factor_by_station(self) -> list:
        """Get power factor for all stations"""
        with self.loss_repo:
            return self.loss_repo.get_power_factor_by_station()
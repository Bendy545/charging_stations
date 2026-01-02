from dataclasses import dataclass
from typing import Optional
from datetime import date, datetime

@dataclass
class LossAnalysis:
    """Domain model for loss analysis"""
    id: Optional[int] = None
    station_id: int = 0
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    total_consumption_kwh: float = 0.0
    total_delivered_kwh: float = 0.0
    total_reactive_kwh: float = 0.0
    loss_kwh: float = 0.0
    loss_percentage: float = 0.0
    calculated_at: Optional[datetime] = None
    station_code: Optional[str] = None
    station_name: Optional[str] = None

    @property
    def power_factor(self) -> float:
        """Calculate power factor"""
        if self.total_reactive_kwh == 0:
            return 100.0
        apparent = (self.total_consumption_kwh**2 + self.total_reactive_kwh**2)**0.5
        return (self.total_consumption_kwh / apparent * 100) if apparent > 0 else 100.0

    @property
    def efficiency(self) -> float:
        """Calculate efficiency percentage"""
        if self.total_consumption_kwh == 0:
            return 0.0
        return (self.total_delivered_kwh / self.total_consumption_kwh) * 100

    @property
    def apparent_power(self) -> float:
        """Calculate apparent power"""
        return (self.total_consumption_kwh**2 + self.total_reactive_kwh**2)**0.5

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'station_id': self.station_id,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'total_consumption_kwh': self.total_consumption_kwh,
            'total_delivered_kwh': self.total_delivered_kwh,
            'total_reactive_kwh': self.total_reactive_kwh,
            'loss_kwh': self.loss_kwh,
            'loss_percentage': self.loss_percentage,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
            'station_code': self.station_code,
            'station_name': self.station_name,
            'power_factor': self.power_factor,
            'efficiency': self.efficiency
        }
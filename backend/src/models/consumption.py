from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class PowerConsumption:
    """Domain model for power consumption"""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    station_id: int = 0
    active_power_kwh: float = 0.0
    reactive_power_kwh: float = 0.0
    station_code: Optional[str] = None
    station_name: Optional[str] = None

    @property
    def apparent_power_kwh(self) -> float:
        """Calculate apparent power"""
        return (self.active_power_kwh**2 + self.reactive_power_kwh**2)**0.5

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'station_id': self.station_id,
            'active_power_kwh': self.active_power_kwh,
            'reactive_power_kwh': self.reactive_power_kwh,
            'station_code': self.station_code,
            'station_name': self.station_name,
            'apparent_power_kwh': self.apparent_power_kwh
        }
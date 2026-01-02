from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class ChargingSession:
    """Domain model for charging session"""
    id: Optional[int] = None
    station_id: int = 0
    charger_name: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_kwh: float = 0.0
    start_card: str = ""
    end_interval_15min: Optional[datetime] = None
    station_code: Optional[str] = None
    station_name: Optional[str] = None

    @property
    def duration_minutes(self) -> float:
        """Calculate session duration in minutes"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).total_seconds() / 60
        return 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'station_id': self.station_id,
            'charger_name': self.charger_name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'total_kwh': self.total_kwh,
            'start_card': self.start_card,
            'end_interval_15min': self.end_interval_15min.isoformat() if self.end_interval_15min else None,
            'station_code': self.station_code,
            'station_name': self.station_name,
            'duration_minutes': self.duration_minutes
        }
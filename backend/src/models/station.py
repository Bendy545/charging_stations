from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Station:
    """Domain model for charging station"""
    id: Optional[int] = None
    station_code: str = ""
    station_name: str = ""
    location: str = "Jeníšov"
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'station_code': self.station_code,
            'station_name': self.station_name,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
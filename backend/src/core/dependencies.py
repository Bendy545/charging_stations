from backend.src.core.database import get_db_connection
from backend.src.repositories import (
    StationRepository,
    LossRepository,
    SessionRepository,
    ConsumptionRepository
)

def get_db():
    """FastAPI dependency for database connection"""
    connection = get_db_connection()
    try:
        yield connection
    finally:
        connection.close()

def get_station_repo(connection=None):
    """Dependency for station repository"""
    return StationRepository(connection)

def get_loss_repo(connection=None):
    """Dependency for loss repository"""
    return LossRepository(connection)

def get_session_repo(connection=None):
    """Dependency for session repository"""
    return SessionRepository(connection)

def get_consumption_repo(connection=None):
    """Dependency for consumption repository"""
    return ConsumptionRepository(connection)
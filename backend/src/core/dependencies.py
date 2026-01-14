from backend.src.repositories import (
    StationRepository,
    LossRepository,
    SessionRepository,
    ConsumptionRepository,
    PredictionRepository
)

def get_prediction_repo():
    with PredictionRepository() as repo:
        yield repo

def get_station_repo():
    with StationRepository() as repo:
        yield repo

def get_loss_repo():
    with LossRepository() as repo:
        yield repo

def get_session_repo():
    with SessionRepository() as repo:
        yield repo

def get_consumption_repo():
    with ConsumptionRepository() as repo:
        yield repo

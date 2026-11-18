"""Modelo de dominio de rides: entidades, estados y reglas del negocio.

Ejemplo: services/inventory/app/domain/model.py
"""
from enum import Enum

from pydantic import BaseModel
    
class RideStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Ride(BaseModel):
    ride_id: str
    user_id: str
    vehicle_id: str
    reservation_id: str | None = None  
    origin_zone: str
    destination_zone: str | None = None
    status: RideStatus
    started_at: str
    finished_at: str | None = None
    duration_min: float | None = None
    cost: float | None = None
    battery_level: int | None = None

class RideNotFound(Exception):
    pass


class RideAlreadyFinished(Exception):
    pass


class VehicleNotAvailable(Exception):
    pass


class AvailabilityServiceDown(Exception):
    pass
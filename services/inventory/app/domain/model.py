"""Modelo de dominio del inventario: qué es un vehículo y sus estados administrativos."""

from datetime import date
from enum import Enum

from pydantic import BaseModel


class VehicleType(str, Enum):
    BIKE = "BIKE"
    SCOOTER = "SCOOTER"


class AdminStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class Vehicle(BaseModel):
    vehicle_type: VehicleType
    model: str
    purchase_date: date
    initial_zone: str
    vehicle_id: str
    admin_status: AdminStatus
    created_at: str


class VehicleNotFound(Exception):
    pass

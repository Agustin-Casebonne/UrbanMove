"""Modelo de dominio de availability: entidades, estados y reglas del negocio.

Ejemplo: services/inventory/app/domain/model.py
"""

from enum import Enum


class VehicleType (str, Enum):
    BIKE = "BIKE"
    SCOOTER = "SCOOTER"

class VehicleStatus (str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    IN_USE = "IN_USE"
    LOW_BATTERY = "LOW_BATTERY"
    WITHDRAWN = "WITHDRAWN"
    CHARGING = "CHARGING"
    REPAIRING = "REPAIRING"
    READY_FOR_SERVICE = "READY_FOR_SERVICE"
    RETIRED = "RETIRED"

S = VehicleStatus

ALLOWED_TRANSITIONS = {
    VehicleStatus.AVAILABLE: [
        VehicleStatus.RESERVED,
        VehicleStatus.IN_USE,
        VehicleStatus.LOW_BATTERY,
        VehicleStatus.WITHDRAWN,
        VehicleStatus.RETIRED,
    ],
    VehicleStatus.RESERVED: [
        VehicleStatus.AVAILABLE,
        VehicleStatus.IN_USE,
        VehicleStatus.WITHDRAWN,
    ],
    VehicleStatus.IN_USE: [
        VehicleStatus.AVAILABLE,
        VehicleStatus.LOW_BATTERY,
    ],
    VehicleStatus.LOW_BATTERY: [
        VehicleStatus.WITHDRAWN,
    ],
    VehicleStatus.WITHDRAWN: [
        VehicleStatus.CHARGING,
        VehicleStatus.REPAIRING,
        VehicleStatus.READY_FOR_SERVICE,
        VehicleStatus.RETIRED,
    ],
    VehicleStatus.CHARGING: [
        VehicleStatus.READY_FOR_SERVICE,
        VehicleStatus.REPAIRING,
    ],
    VehicleStatus.REPAIRING: [
        VehicleStatus.READY_FOR_SERVICE,
        VehicleStatus.RETIRED,
    ],
    VehicleStatus.READY_FOR_SERVICE: [
        VehicleStatus.AVAILABLE,
    ],
    VehicleStatus.RETIRED: [],  # estado final: no puede pasar a ninguno
}


def can_transition(current: VehicleStatus, new: VehicleStatus) -> bool:
    return new in ALLOWED_TRANSITIONS[current]


class Vehicle(BaseModel):
    vehicle_id: str
    vehicle_type: VehicleType
    zone_id: str
    status: VehicleStatus
    battery_level: int | None = None
    updated_at: str


class VehicleNotFound(Exception):
    pass


class InvalidTransition(Exception):
    def __init__(self, vehicle_id: str, current: VehicleStatus, new: VehicleStatus):
        super().__init__(f"El vehículo {vehicle_id} no puede pasar de {current.value} a {new.value}")

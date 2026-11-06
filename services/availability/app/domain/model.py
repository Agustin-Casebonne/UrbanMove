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



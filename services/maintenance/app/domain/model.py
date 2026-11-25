"""Modelo de dominio de maintenance: entidades, estados y reglas del negocio.

Ejemplo: services/inventory/app/domain/model.py

Ciclo de vida de una orden de mantenimiento:

    OPEN ──assign──> ASSIGNED ──start──> IN_PROGRESS ──complete──> COMPLETED

- Solo se avanza de uno en uno: no se puede saltar ni retroceder estados.
- OPEN, ASSIGNED e IN_PROGRESS son estados ACTIVOS: el vehículo tiene una orden
  en curso y no se crea otra para él.
- COMPLETED es el estado FINAL: ya no cambia.
"""

from enum import Enum

from pydantic import BaseModel


class MaintenanceType(str, Enum):
    CHARGE = "CHARGE"
    REPAIR = "REPAIR"
    REVIEW = "REVIEW"


class MaintenanceStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class MaintenanceOrder(BaseModel):
    order_id: str
    vehicle_id: str
    type: MaintenanceType
    status: MaintenanceStatus
    reason: str
    created_at: str
    updated_at: str


class MaintenanceOrderNotFound(Exception):
    pass


class InvalidTransition(Exception):
    """La acción no está permitida en el estado actual de la orden."""

    def __init__(self, order_id: str, current: MaintenanceStatus, action: str):
        self.current = current
        super().__init__(f"No se puede {action} la orden {order_id} en estado {current.value}")


class OrderAlreadyOpen(Exception):
    """El vehículo ya tiene una orden activa (idempotencia: VehicleBatteryLow repetido)."""

"""Modelo de dominio de relocation: entidades, estados y reglas del negocio.

Ejemplo: services/inventory/app/domain/model.py

Ciclo de vida de una orden de recolocación:

    OPEN ──assign──> ASSIGNED ──start──> IN_PROGRESS ──complete──> COMPLETED

- Solo se avanza de uno en uno: no se puede saltar ni retroceder estados.
- OPEN, ASSIGNED e IN_PROGRESS son estados ACTIVOS: hay una orden en curso para
  ese trayecto y tipo de vehículo (from_zone → to_zone, vehicle_type) y no se
  crea otra igual (idempotencia: la Lambda de recolocación puede detectar el
  mismo déficit más de una vez).
- COMPLETED es el estado FINAL: ya no cambia.
"""

from enum import Enum

from pydantic import BaseModel


class VehicleType(str, Enum):
    BIKE = "BIKE"
    SCOOTER = "SCOOTER"


class RelocationStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class RelocationOrder(BaseModel):
    order_id: str
    from_zone: str
    to_zone: str
    vehicle_type: VehicleType
    quantity: int
    reason: str
    status: RelocationStatus
    vehicle_ids: list[str] = []
    created_at: str
    updated_at: str
    completed_at: str | None = None


class RelocationOrderNotFound(Exception):
    pass


class InvalidTransition(Exception):
    """La acción no está permitida en el estado actual de la orden."""

    def __init__(self, order_id: str, current: RelocationStatus, action: str):
        self.current = current
        super().__init__(
            f"No se puede {action} la orden de recolocación {order_id} en estado {current.value}"
        )


class OrderAlreadyOpen(Exception):
    """Ya hay una orden activa para el mismo from_zone → to_zone y vehicle_type."""

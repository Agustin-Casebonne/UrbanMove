"""Modelo de dominio de reservations: qué es una reserva, sus estados y sus errores.

Ciclo de vida de una reserva:

    PENDING ──confirm──> CONFIRMED ──fulfill──> FULFILLED
       │                    │
       ├──cancel / expire───┴──> CANCELLED / EXPIRED

- PENDING y CONFIRMED son estados ACTIVOS: el vehículo está bloqueado para
  ese usuario y nadie más puede reservarlo.
- FULFILLED, CANCELLED y EXPIRED son estados FINALES: ya no cambian.
"""

from enum import Enum

from pydantic import BaseModel


class VehicleType(str, Enum):
    BIKE = "BIKE"
    SCOOTER = "SCOOTER"


class ReservationStatus(str, Enum):
    PENDING = "PENDING"  # creada, esperando confirmación del usuario
    CONFIRMED = "CONFIRMED"  # confirmada: el vehículo se guarda un rato más
    FULFILLED = "FULFILLED"  # el usuario empezó el viaje (lo marca rides)
    CANCELLED = "CANCELLED"  # cancelada por el usuario
    EXPIRED = "EXPIRED"  # caducada por tiempo (Lambda de expiración)


ACTIVE_STATUSES = (ReservationStatus.PENDING, ReservationStatus.CONFIRMED)


class Reservation(BaseModel):
    reservation_id: str
    user_id: str
    vehicle_id: str
    vehicle_type: VehicleType
    zone_id: str
    status: ReservationStatus
    created_at: str
    expires_at: str
    updated_at: str


# --- Errores de dominio (adapters/api.py los traduce a códigos HTTP) ---


class ReservationNotFound(Exception):
    pass


class VehicleAlreadyReserved(Exception):
    """El vehículo ya tiene una reserva activa (evita la doble reserva)."""


class UserAlreadyHasReservation(Exception):
    """El usuario ya tiene otra reserva activa."""


class InvalidTransition(Exception):
    """La acción no está permitida en el estado actual de la reserva."""

    def __init__(self, reservation_id: str, current: ReservationStatus, action: str):
        self.current = current
        super().__init__(f"No se puede {action} la reserva {reservation_id} en estado {current.value}")


class ReservationNotYetExpired(Exception):
    """Se pidió expirar una reserva cuyo plazo todavía no ha vencido."""


class VehicleNotFound(Exception):
    """El servicio de disponibilidad no conoce el vehículo."""


class VehicleNotAvailable(Exception):
    """El vehículo existe pero no está AVAILABLE (en uso, en carga, retirado...)."""


class AvailabilityServiceDown(Exception):
    """No se pudo consultar el servicio de disponibilidad (caído o timeout)."""

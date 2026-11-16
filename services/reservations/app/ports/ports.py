"""Puertos: contratos entre el dominio de reservations y el exterior.

El dominio solo conoce estas interfaces. Las implementaciones concretas
están en adapters/ y se conectan en main.py:
- ReservationRepository -> adapters/db.py (SQLite)
- EventPublisher        -> adapters/events.py (SNS)
- AvailabilityChecker   -> adapters/availability.py (HTTP al servicio availability)
"""

from typing import Protocol

from ..domain.model import Reservation, ReservationStatus


class ReservationRepository(Protocol):
    def ping(self) -> None: ...

    def create(self, reservation: Reservation) -> None:
        """Guarda una reserva nueva.

        Lanza VehicleAlreadyReserved o UserAlreadyHasReservation si ya
        existe una reserva activa para ese vehículo o ese usuario.
        """
        ...

    def get(self, reservation_id: str) -> Reservation | None: ...

    def list_reservations(
        self, user_id: str | None = None, status: ReservationStatus | None = None
    ) -> list[Reservation]: ...

    def list_overdue(self, now_iso: str) -> list[Reservation]:
        """Reservas activas cuyo expires_at ya ha pasado."""
        ...

    def transition(
        self,
        reservation_id: str,
        from_statuses: tuple[ReservationStatus, ...],
        to_status: ReservationStatus,
        updated_at: str,
        expires_at: str | None = None,
    ) -> bool:
        """Cambia el estado SOLO si el estado actual está en from_statuses.

        Devuelve False si no se cambió (otra petición se adelantó).
        """
        ...


class EventPublisher(Protocol):
    def publish(self, event_type: str, data: dict) -> None: ...


class AvailabilityChecker(Protocol):
    def check_vehicle(self, vehicle_id: str) -> None:
        """No devuelve nada si el vehículo está AVAILABLE.

        Lanza VehicleNotFound, VehicleNotAvailable o AvailabilityServiceDown.
        """
        ...

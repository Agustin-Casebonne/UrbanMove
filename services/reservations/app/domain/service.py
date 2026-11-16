"""Lógica de negocio de reservations.

Solo depende del modelo y de los puertos: no sabe que existen FastAPI,
SQLite ni SNS.

Reglas principales:
- Un vehículo no puede tener dos reservas activas a la vez (lo garantiza
  un índice único en la base de datos, ver adapters/db.py).
- Un usuario no puede tener dos reservas activas a la vez.
- Una reserva PENDING caduca a los `pending_ttl_minutes`. Al confirmarla, el
  vehículo se guarda `confirmed_hold_minutes` más; si no se usa, también caduca.
- Las operaciones repetidas son idempotentes: cancelar una reserva ya
  cancelada o expirar una ya expirada devuelve la reserva sin publicar
  otro evento.
"""

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from ..ports.ports import AvailabilityChecker, EventPublisher, ReservationRepository
from .model import (
    ACTIVE_STATUSES,
    InvalidTransition,
    Reservation,
    ReservationNotFound,
    ReservationNotYetExpired,
    ReservationStatus,
    VehicleType,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    # Siempre el mismo formato (UTC, sin microsegundos) para poder comparar
    # fechas como texto en SQL.
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


class ReservationService:
    def __init__(
        self,
        repository: ReservationRepository,
        publisher: EventPublisher,
        availability: AvailabilityChecker | None = None,
        pending_ttl_minutes: float = 5,
        confirmed_hold_minutes: float = 15,
        clock: Callable[[], datetime] = utc_now,
    ):
        self.repository = repository
        self.publisher = publisher
        self.availability = availability
        self.pending_ttl = timedelta(minutes=pending_ttl_minutes)
        self.confirmed_hold = timedelta(minutes=confirmed_hold_minutes)
        self.clock = clock

    def check_health(self) -> None:
        self.repository.ping()

    # ---------- consultas ----------

    def get_reservation(self, reservation_id: str) -> Reservation:
        reservation = self.repository.get(reservation_id)
        if reservation is None:
            raise ReservationNotFound(reservation_id)
        return reservation

    def list_reservations(
        self, user_id: str | None = None, status: ReservationStatus | None = None
    ) -> list[Reservation]:
        return self.repository.list_reservations(user_id=user_id, status=status)

    # ---------- comandos ----------

    def create_reservation(
        self, user_id: str, vehicle_id: str, vehicle_type: VehicleType, zone_id: str
    ) -> Reservation:
        # 1. Si hay servicio de disponibilidad configurado, se comprueba que el
        #    vehículo está AVAILABLE. Si está caído, se rechaza la reserva (503):
        #    es preferible no reservar a reservar algo que quizá no existe.
        if self.availability is not None:
            self.availability.check_vehicle(vehicle_id)

        now = self.clock()
        reservation = Reservation(
            reservation_id=f"R-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            vehicle_id=vehicle_id,
            vehicle_type=vehicle_type,
            zone_id=zone_id,
            status=ReservationStatus.PENDING,
            created_at=to_iso(now),
            expires_at=to_iso(now + self.pending_ttl),
            updated_at=to_iso(now),
        )
        # 2. Se guarda. El índice único de la BD rechaza la doble reserva,
        #    incluso si llegan dos peticiones exactamente a la vez.
        self.repository.create(reservation)
        # 3. Primero se guarda y DESPUÉS se publica el evento.
        self.publisher.publish(
            "VehicleReserved",
            {
                "reservation_id": reservation.reservation_id,
                "user_id": user_id,
                "vehicle_id": vehicle_id,
                "vehicle_type": vehicle_type.value,
                "zone_id": zone_id,
                "expires_at": reservation.expires_at,
            },
        )
        return reservation

    def confirm(self, reservation_id: str) -> Reservation:
        reservation = self.get_reservation(reservation_id)
        if reservation.status == ReservationStatus.CONFIRMED:
            return reservation  # idempotente
        if reservation.status != ReservationStatus.PENDING:
            raise InvalidTransition(reservation_id, reservation.status, "confirmar")
        if self._is_overdue(reservation):
            # La Lambda aún no ha pasado, pero el plazo ya venció: se expira aquí.
            self._expire(reservation)
            raise InvalidTransition(reservation_id, ReservationStatus.EXPIRED, "confirmar")

        now = self.clock()
        changed = self.repository.transition(
            reservation_id,
            (ReservationStatus.PENDING,),
            ReservationStatus.CONFIRMED,
            updated_at=to_iso(now),
            expires_at=to_iso(now + self.confirmed_hold),
        )
        if not changed:
            current = self.get_reservation(reservation_id)
            raise InvalidTransition(reservation_id, current.status, "confirmar")
        return self.get_reservation(reservation_id)

    def cancel(self, reservation_id: str) -> Reservation:
        reservation = self.get_reservation(reservation_id)
        if reservation.status == ReservationStatus.CANCELLED:
            return reservation  # idempotente
        if reservation.status not in ACTIVE_STATUSES:
            raise InvalidTransition(reservation_id, reservation.status, "cancelar")

        changed = self.repository.transition(
            reservation_id, ACTIVE_STATUSES, ReservationStatus.CANCELLED, updated_at=to_iso(self.clock())
        )
        if not changed:
            current = self.get_reservation(reservation_id)
            raise InvalidTransition(reservation_id, current.status, "cancelar")

        self.publisher.publish(
            "ReservationCancelled",
            {
                "reservation_id": reservation_id,
                "user_id": reservation.user_id,
                "vehicle_id": reservation.vehicle_id,
                "zone_id": reservation.zone_id,
            },
        )
        return self.get_reservation(reservation_id)

    def expire(self, reservation_id: str) -> Reservation:
        """Expira UNA reserva. Lo usa la Lambda de expiración."""
        reservation = self.get_reservation(reservation_id)
        if reservation.status == ReservationStatus.EXPIRED:
            return reservation  # idempotente: la Lambda puede reintentar sin duplicar eventos
        if reservation.status not in ACTIVE_STATUSES:
            raise InvalidTransition(reservation_id, reservation.status, "expirar")
        if not self._is_overdue(reservation):
            raise ReservationNotYetExpired(reservation_id)

        if not self._expire(reservation):
            current = self.get_reservation(reservation_id)
            if current.status != ReservationStatus.EXPIRED:
                raise InvalidTransition(reservation_id, current.status, "expirar")
        return self.get_reservation(reservation_id)

    def expire_overdue(self) -> list[Reservation]:
        """Expira TODAS las reservas activas vencidas. Devuelve las que expiró."""
        expired = []
        for reservation in self.repository.list_overdue(to_iso(self.clock())):
            if self._expire(reservation):
                expired.append(self.get_reservation(reservation.reservation_id))
        return expired

    def fulfill(self, reservation_id: str) -> Reservation:
        """Marca la reserva como usada. Lo llama rides al iniciar el viaje."""
        reservation = self.get_reservation(reservation_id)
        if reservation.status == ReservationStatus.FULFILLED:
            return reservation  # idempotente
        if reservation.status not in ACTIVE_STATUSES:
            raise InvalidTransition(reservation_id, reservation.status, "usar")
        if self._is_overdue(reservation):
            self._expire(reservation)
            raise InvalidTransition(reservation_id, ReservationStatus.EXPIRED, "usar")

        changed = self.repository.transition(
            reservation_id, ACTIVE_STATUSES, ReservationStatus.FULFILLED, updated_at=to_iso(self.clock())
        )
        if not changed:
            current = self.get_reservation(reservation_id)
            raise InvalidTransition(reservation_id, current.status, "usar")
        # No se publica evento propio: rides publica RideStarted.
        return self.get_reservation(reservation_id)

    # ---------- auxiliares ----------

    def _is_overdue(self, reservation: Reservation) -> bool:
        return self.clock() >= datetime.fromisoformat(reservation.expires_at)

    def _expire(self, reservation: Reservation) -> bool:
        """Pasa la reserva a EXPIRED y publica el evento. False si otro se adelantó."""
        changed = self.repository.transition(
            reservation.reservation_id,
            ACTIVE_STATUSES,
            ReservationStatus.EXPIRED,
            updated_at=to_iso(self.clock()),
        )
        if changed:
            self.publisher.publish(
                "ReservationExpired",
                {
                    "reservation_id": reservation.reservation_id,
                    "user_id": reservation.user_id,
                    "vehicle_id": reservation.vehicle_id,
                    "zone_id": reservation.zone_id,
                },
            )
        return changed

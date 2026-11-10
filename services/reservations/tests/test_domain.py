"""Tests de la lógica de negocio con la base de datos SQLite real.

No usan FastAPI ni SNS: el publicador de eventos es falso y el reloj se
controla desde el test para simular el paso del tiempo.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.adapters.db import SqliteReservationRepository, init_db
from app.domain.model import (
    AvailabilityServiceDown,
    InvalidTransition,
    ReservationNotYetExpired,
    ReservationStatus,
    UserAlreadyHasReservation,
    VehicleAlreadyReserved,
    VehicleNotAvailable,
    VehicleType,
)
from app.domain.service import ReservationService


class FakePublisher:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def publish(self, event_type: str, data: dict) -> None:
        self.events.append((event_type, data))

    def types(self) -> list[str]:
        return [t for t, _ in self.events]


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, minutes: float) -> None:
        self.now += timedelta(minutes=minutes)


class FakeAvailability:
    def __init__(self, error: Exception | None = None):
        self.error = error

    def check_vehicle(self, vehicle_id: str) -> None:
        if self.error:
            raise self.error


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    init_db()
    publisher, clock = FakePublisher(), FakeClock()
    service = ReservationService(
        SqliteReservationRepository(),
        publisher,
        pending_ttl_minutes=5,
        confirmed_hold_minutes=15,
        clock=clock,
    )
    return service, publisher, clock


def reserve(service, user="U1", vehicle="S-1", zone="Z01"):
    return service.create_reservation(user, vehicle, VehicleType.SCOOTER, zone)


def test_create_publishes_vehicle_reserved(ctx):
    service, publisher, _ = ctx
    r = reserve(service)
    assert r.status == ReservationStatus.PENDING
    assert r.expires_at == "2026-11-10T12:05:00+00:00"
    assert publisher.types() == ["VehicleReserved"]
    assert publisher.events[0][1]["vehicle_id"] == "S-1"


def test_same_vehicle_cannot_be_reserved_twice(ctx):
    service, publisher, _ = ctx
    reserve(service, user="U1")
    with pytest.raises(VehicleAlreadyReserved):
        reserve(service, user="U2")
    assert publisher.types() == ["VehicleReserved"]  # el segundo intento no publica nada


def test_user_cannot_have_two_active_reservations(ctx):
    service, _, _ = ctx
    reserve(service, vehicle="S-1")
    with pytest.raises(UserAlreadyHasReservation):
        reserve(service, vehicle="S-2")


def test_vehicle_can_be_reserved_again_after_cancel(ctx):
    service, _, _ = ctx
    first = reserve(service, user="U1")
    service.cancel(first.reservation_id)
    second = reserve(service, user="U2")
    assert second.status == ReservationStatus.PENDING


def test_confirm_extends_hold(ctx):
    service, _, clock = ctx
    r = reserve(service)
    clock.advance(2)
    confirmed = service.confirm(r.reservation_id)
    assert confirmed.status == ReservationStatus.CONFIRMED
    assert confirmed.expires_at == "2026-11-10T12:17:00+00:00"


def test_confirm_after_deadline_expires_reservation(ctx):
    service, publisher, clock = ctx
    r = reserve(service)
    clock.advance(6)
    with pytest.raises(InvalidTransition):
        service.confirm(r.reservation_id)
    assert service.get_reservation(r.reservation_id).status == ReservationStatus.EXPIRED
    assert publisher.types() == ["VehicleReserved", "ReservationExpired"]


def test_cancel_is_idempotent(ctx):
    service, publisher, _ = ctx
    r = reserve(service)
    service.cancel(r.reservation_id)
    again = service.cancel(r.reservation_id)
    assert again.status == ReservationStatus.CANCELLED
    assert publisher.types().count("ReservationCancelled") == 1


def test_expire_before_deadline_is_rejected(ctx):
    service, _, _ = ctx
    r = reserve(service)
    with pytest.raises(ReservationNotYetExpired):
        service.expire(r.reservation_id)


def test_expire_is_idempotent(ctx):
    service, publisher, clock = ctx
    r = reserve(service)
    clock.advance(5)
    service.expire(r.reservation_id)
    service.expire(r.reservation_id)  # la Lambda reintenta
    assert publisher.types().count("ReservationExpired") == 1


def test_expire_overdue_only_touches_overdue(ctx):
    service, publisher, clock = ctx
    old = reserve(service, user="U1", vehicle="S-1")
    clock.advance(4)
    recent = reserve(service, user="U2", vehicle="S-2")
    clock.advance(1)  # old cumple 5 min, recent solo 1

    expired = service.expire_overdue()

    assert [r.reservation_id for r in expired] == [old.reservation_id]
    assert service.get_reservation(recent.reservation_id).status == ReservationStatus.PENDING
    assert service.expire_overdue() == []  # segunda pasada: nada nuevo
    assert publisher.types().count("ReservationExpired") == 1


def test_cancelled_reservation_cannot_be_confirmed(ctx):
    service, _, _ = ctx
    r = reserve(service)
    service.cancel(r.reservation_id)
    with pytest.raises(InvalidTransition):
        service.confirm(r.reservation_id)


def test_fulfill_marks_reservation_used(ctx):
    service, _, _ = ctx
    r = reserve(service)
    service.confirm(r.reservation_id)
    used = service.fulfill(r.reservation_id)
    assert used.status == ReservationStatus.FULFILLED
    # El vehículo vuelve a poder reservarse cuando acabe el viaje (lo decide availability).
    reserve(service, user="U2")


def test_list_by_user(ctx):
    service, _, _ = ctx
    r = reserve(service, user="U1", vehicle="S-1")
    service.cancel(r.reservation_id)
    reserve(service, user="U1", vehicle="S-2")
    reserve(service, user="U2", vehicle="S-3")
    assert len(service.list_reservations(user_id="U1")) == 2
    assert len(service.list_reservations(user_id="U1", status=ReservationStatus.CANCELLED)) == 1


def test_unavailable_vehicle_is_rejected(ctx):
    service, publisher, _ = ctx
    service.availability = FakeAvailability(VehicleNotAvailable("S-1 está en estado CHARGING"))
    with pytest.raises(VehicleNotAvailable):
        reserve(service)
    assert publisher.events == []


def test_availability_down_rejects_without_saving(ctx):
    service, _, _ = ctx
    service.availability = FakeAvailability(AvailabilityServiceDown("timeout"))
    with pytest.raises(AvailabilityServiceDown):
        reserve(service)
    assert service.list_reservations() == []

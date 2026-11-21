"""Tests de la lógica de negocio de rides con repositorio y publisher falsos."""

from datetime import datetime, timedelta, timezone

import pytest

from app.domain.model import RideNotFound, RideStatus, VehicleNotAvailable
from app.domain.service import RideService


class FakeRepo:
    def __init__(self):
        self.rides = {}

    def ping(self):
        pass

    def save(self, ride):
        self.rides[ride.ride_id] = ride

    def get(self, ride_id):
        return self.rides.get(ride_id)

    def list_rides(self, user_id=None, status=None):
        return list(self.rides.values())


class FakePublisher:
    def __init__(self):
        self.events = []

    def publish(self, event_type, data):
        self.events.append(event_type)


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, minutes):
        self.now += timedelta(minutes=minutes)


class BadChecker:
    def check_vehicle(self, vehicle_id):
        raise VehicleNotAvailable("no disponible")


@pytest.fixture
def repo():
    return FakeRepo()


@pytest.fixture
def publisher():
    return FakePublisher()


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def service(repo, publisher, clock):
    return RideService(repo, None, publisher, clock)


def test_start_ride(service, publisher):
    ride = service.start_ride("u1", "v1", "centro")
    assert ride.status == RideStatus.IN_PROGRESS
    assert publisher.events == ["RideStarted"]


def test_finish_ride_calcula_duracion_y_coste(service, publisher, clock):
    ride = service.start_ride("u1", "v1", "centro")
    clock.advance(10)
    done = service.finish_ride(ride.ride_id, "norte")
    assert done.status == RideStatus.FINISHED
    assert done.duration_min == 10
    assert done.cost == 2.0
    assert publisher.events == ["RideStarted", "RideFinished"]


def test_finish_dos_veces_publica_un_solo_evento(service, publisher, clock):
    ride = service.start_ride("u1", "v1", "centro")
    clock.advance(10)
    service.finish_ride(ride.ride_id, "norte")
    service.finish_ride(ride.ride_id, "norte")
    assert publisher.events.count("RideFinished") == 1


def test_finish_viaje_inexistente(service):
    with pytest.raises(RideNotFound):
        service.finish_ride("no-existe", "norte")


def test_vehiculo_no_disponible_no_guarda_ni_publica(repo, publisher, clock):
    service = RideService(repo, BadChecker(), publisher, clock)
    with pytest.raises(VehicleNotAvailable):
        service.start_ride("u1", "v1", "centro")
    assert repo.rides == {}
    assert publisher.events == []

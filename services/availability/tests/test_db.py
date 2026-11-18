import pytest

from app.adapters.db import SqliteVehicleRepository, init_db
from app.domain.model import Vehicle, VehicleStatus, VehicleType


@pytest.fixture
def repo(tmp_path, monkeypatch):
    # Cada test usa una base de datos nueva y vacía en una carpeta temporal
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    init_db()
    return SqliteVehicleRepository()


def make_vehicle(vehicle_id="S-1", zone_id="Z01", status=VehicleStatus.AVAILABLE):
    return Vehicle(
        vehicle_id=vehicle_id,
        vehicle_type=VehicleType.SCOOTER,
        zone_id=zone_id,
        status=status,
        battery_level=80,
        updated_at="2026-11-17T10:00:00+00:00",
    )


def test_guardar_y_leer(repo):
    repo.save(make_vehicle())
    vehicle = repo.get("S-1")
    assert vehicle.status == VehicleStatus.AVAILABLE
    assert vehicle.zone_id == "Z01"


def test_vehiculo_que_no_existe(repo):
    assert repo.get("NO-EXISTE") is None


def test_guardar_otra_vez_actualiza(repo):
    repo.save(make_vehicle())
    repo.save(make_vehicle(status=VehicleStatus.RESERVED))
    assert repo.get("S-1").status == VehicleStatus.RESERVED


def test_filtrar_por_zona(repo):
    repo.save(make_vehicle("S-1", zone_id="Z01"))
    repo.save(make_vehicle("S-2", zone_id="Z02"))
    result = repo.list_vehicles(zone_id="Z01")
    assert [v.vehicle_id for v in result] == ["S-1"]


def test_evento_procesado(repo):
    assert not repo.is_event_processed("ev-1")
    repo.mark_event_processed("ev-1", "2026-11-17T10:00:00+00:00")
    assert repo.is_event_processed("ev-1")

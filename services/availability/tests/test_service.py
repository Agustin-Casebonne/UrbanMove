"""Tests del servicio. Usan la base de datos real (en una carpeta temporal)
y un publicador falso que solo apunta los eventos en una lista."""

import pytest

from app.adapters.db import SqliteVehicleRepository, init_db
from app.domain.model import InvalidTransition, VehicleNotFound, VehicleStatus
from app.domain.service import AvailabilityService


class FakePublisher:
    """Publicador falso: en vez de enviar a SNS, guarda los eventos en una lista."""

    def __init__(self):
        self.events = []

    def publish(self, event_type, data):
        self.events.append((event_type, data))


@pytest.fixture
def publisher():
    return FakePublisher()


@pytest.fixture
def service(tmp_path, monkeypatch, publisher):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    init_db()
    return AvailabilityService(SqliteVehicleRepository(), publisher)


def make_event(event_type, data, event_id="ev-1"):
    """Crea un evento con la misma forma que los de la cola."""
    return {"event_id": event_id, "event_type": event_type, "data": data}


# ---------- registrar y cambiar de estado ----------


def test_registrar_vehiculo(service):
    vehicle = service.register_vehicle("S-1", "SCOOTER", "Z01")
    assert vehicle.status == VehicleStatus.AVAILABLE
    assert service.get_vehicle("S-1").zone_id == "Z01"


def test_vehiculo_que_no_existe(service):
    with pytest.raises(VehicleNotFound):
        service.get_vehicle("NO-EXISTE")


def test_transicion_valida(service):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    vehicle = service.transition("S-1", VehicleStatus.RESERVED)
    assert vehicle.status == VehicleStatus.RESERVED


def test_transicion_invalida(service):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    with pytest.raises(InvalidTransition):
        service.transition("S-1", VehicleStatus.CHARGING)  # AVAILABLE -> CHARGING no está permitido


# ---------- batería ----------


def test_bateria_baja_publica_evento(service, publisher):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    vehicle = service.report_battery("S-1", 10)
    assert vehicle.status == VehicleStatus.LOW_BATTERY
    assert publisher.events[0][0] == "VehicleBatteryLow"


def test_bateria_normal_no_publica(service, publisher):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    vehicle = service.report_battery("S-1", 60)
    assert vehicle.status == VehicleStatus.AVAILABLE
    assert publisher.events == []


# ---------- eventos ----------


def test_evento_compra_crea_vehiculo(service):
    event = make_event(
        "VehiclePurchased", {"vehicle_id": "B-1", "vehicle_type": "BIKE", "initial_zone": "Z02"}
    )
    assert service.handle_event(event) is True
    assert service.get_vehicle("B-1").status == VehicleStatus.AVAILABLE


def test_flujo_reserva_y_viaje(service):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    service.handle_event(make_event("VehicleReserved", {"vehicle_id": "S-1"}, "ev-1"))
    assert service.get_vehicle("S-1").status == VehicleStatus.RESERVED

    service.handle_event(make_event("RideStarted", {"vehicle_id": "S-1"}, "ev-2"))
    assert service.get_vehicle("S-1").status == VehicleStatus.IN_USE

    service.handle_event(
        make_event(
            "RideFinished",
            {"vehicle_id": "S-1", "destination_zone": "Z05", "battery_level": 70},
            "ev-3",
        )
    )
    vehicle = service.get_vehicle("S-1")
    assert vehicle.status == VehicleStatus.AVAILABLE
    assert vehicle.zone_id == "Z05"  # ahora está en la zona donde acabó el viaje


def test_viaje_termina_con_bateria_baja(service):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    service.transition("S-1", VehicleStatus.IN_USE)
    service.handle_event(
        make_event("RideFinished", {"vehicle_id": "S-1", "destination_zone": "Z02", "battery_level": 5})
    )
    assert service.get_vehicle("S-1").status == VehicleStatus.LOW_BATTERY


def test_cancelar_reserva_libera_vehiculo(service):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    service.transition("S-1", VehicleStatus.RESERVED)
    service.handle_event(make_event("ReservationCancelled", {"vehicle_id": "S-1"}))
    assert service.get_vehicle("S-1").status == VehicleStatus.AVAILABLE


def test_vuelta_de_mantenimiento(service):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    service.handle_event(make_event("VehicleWithdrawnForMaintenance", {"vehicle_id": "S-1"}, "ev-1"))
    assert service.get_vehicle("S-1").status == VehicleStatus.WITHDRAWN

    service.handle_event(
        make_event("VehicleReturnedToService", {"vehicle_id": "S-1", "zone_id": "Z03"}, "ev-2")
    )
    vehicle = service.get_vehicle("S-1")
    assert vehicle.status == VehicleStatus.AVAILABLE
    assert vehicle.zone_id == "Z03"


def test_recolocacion_cambia_zona(service):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    service.register_vehicle("S-2", "SCOOTER", "Z01")
    service.handle_event(
        make_event("RelocationOrderCompleted", {"vehicle_ids": ["S-1", "S-2"], "to_zone": "Z09"})
    )
    assert service.get_vehicle("S-1").zone_id == "Z09"
    assert service.get_vehicle("S-2").zone_id == "Z09"


def test_evento_duplicado_se_ignora(service):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    event = make_event("VehicleReserved", {"vehicle_id": "S-1"})
    assert service.handle_event(event) is True
    assert service.handle_event(event) is False  # mismo event_id: no se aplica dos veces


def test_evento_desordenado_se_descarta(service):
    service.register_vehicle("S-1", "SCOOTER", "Z01")
    # RideFinished sobre un vehículo AVAILABLE (nunca empezó el viaje): no encaja
    event = make_event("RideFinished", {"vehicle_id": "S-1", "destination_zone": "Z02", "battery_level": 50})
    assert service.handle_event(event) is False
    assert service.get_vehicle("S-1").status == VehicleStatus.AVAILABLE  # no ha cambiado

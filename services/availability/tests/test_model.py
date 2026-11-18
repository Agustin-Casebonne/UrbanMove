from app.domain.model import VehicleStatus, can_transition


def test_transicion_valida():
    assert can_transition(VehicleStatus.AVAILABLE, VehicleStatus.RESERVED)


def test_transicion_invalida():
    assert not can_transition(VehicleStatus.LOW_BATTERY, VehicleStatus.RESERVED)


def test_retirado_es_final():
    assert not can_transition(VehicleStatus.RETIRED, VehicleStatus.AVAILABLE)

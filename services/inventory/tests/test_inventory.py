import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("EVENTS_TOPIC_ARN", raising=False)
    from app.main import app

    with TestClient(app) as c:
        yield c


NEW_VEHICLE = {
    "vehicle_type": "SCOOTER",
    "model": "Xiaomi Pro 2",
    "purchase_date": "2026-09-01",
    "initial_zone": "Z01",
}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_get_vehicle(client):
    r = client.post("/vehicles", json=NEW_VEHICLE)
    assert r.status_code == 201
    vehicle = r.json()
    assert vehicle["admin_status"] == "ACTIVE"
    assert vehicle["vehicle_id"].startswith("S-")

    r = client.get(f"/vehicles/{vehicle['vehicle_id']}")
    assert r.status_code == 200
    assert r.json()["model"] == "Xiaomi Pro 2"


def test_list_vehicles(client):
    client.post("/vehicles", json=NEW_VEHICLE)
    client.post("/vehicles", json={**NEW_VEHICLE, "vehicle_type": "BIKE"})
    r = client.get("/vehicles")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_invalid_type_is_rejected(client):
    r = client.post("/vehicles", json={**NEW_VEHICLE, "vehicle_type": "CAR"})
    assert r.status_code == 422


def test_retire_vehicle(client):
    vid = client.post("/vehicles", json=NEW_VEHICLE).json()["vehicle_id"]
    r = client.patch(f"/vehicles/{vid}/admin-status", json={"admin_status": "RETIRED"})
    assert r.status_code == 200
    assert r.json()["admin_status"] == "RETIRED"


def test_unknown_vehicle_returns_404(client):
    assert client.get("/vehicles/X-000").status_code == 404


def test_correlation_id_is_propagated(client):
    r = client.get("/vehicles", headers={"X-Correlation-ID": "abc-123"})
    assert r.headers["X-Correlation-ID"] == "abc-123"

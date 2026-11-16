"""Tests de la API REST (FastAPI TestClient)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("EVENTS_TOPIC_ARN", raising=False)
    monkeypatch.delenv("AVAILABILITY_URL", raising=False)

    def _make(ttl_minutes: str = "5"):
        monkeypatch.setenv("RESERVATION_TTL_MINUTES", ttl_minutes)
        from app.main import app

        return TestClient(app)

    return _make


@pytest.fixture
def client(make_client):
    with make_client() as c:
        yield c


NEW = {"user_id": "U1", "vehicle_id": "S-1", "vehicle_type": "SCOOTER", "zone_id": "Z01"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "reservations"


def test_create_and_get(client):
    r = client.post("/reservations", json=NEW)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "PENDING"

    r = client.get(f"/reservations/{body['reservation_id']}")
    assert r.status_code == 200
    assert r.json()["vehicle_id"] == "S-1"


def test_double_reservation_returns_409(client):
    assert client.post("/reservations", json=NEW).status_code == 201
    r = client.post("/reservations", json={**NEW, "user_id": "U2"})
    assert r.status_code == 409
    assert "reserva activa" in r.json()["detail"]


def test_confirm_and_cancel(client):
    rid = client.post("/reservations", json=NEW).json()["reservation_id"]
    assert client.post(f"/reservations/{rid}/confirm").json()["status"] == "CONFIRMED"
    assert client.post(f"/reservations/{rid}/cancel").json()["status"] == "CANCELLED"
    r = client.post(f"/reservations/{rid}/confirm")
    assert r.status_code == 409


def test_list_by_user(client):
    client.post("/reservations", json=NEW)
    client.post("/reservations", json={**NEW, "user_id": "U2", "vehicle_id": "S-2"})
    r = client.get("/reservations", params={"user_id": "U1"})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_expire_not_yet_due_returns_409(client):
    rid = client.post("/reservations", json=NEW).json()["reservation_id"]
    assert client.post(f"/reservations/{rid}/expire").status_code == 409


def test_expire_overdue(make_client):
    with make_client(ttl_minutes="0") as client:  # caducan nada más crearse
        rid = client.post("/reservations", json=NEW).json()["reservation_id"]
        r = client.post("/reservations/expire-overdue")
        assert r.status_code == 200
        assert [x["reservation_id"] for x in r.json()] == [rid]
        assert client.get(f"/reservations/{rid}").json()["status"] == "EXPIRED"


def test_unknown_reservation_returns_404(client):
    assert client.get("/reservations/R-nope").status_code == 404
    assert client.post("/reservations/R-nope/cancel").status_code == 404


def test_invalid_vehicle_type_returns_422(client):
    assert client.post("/reservations", json={**NEW, "vehicle_type": "CAR"}).status_code == 422


def test_correlation_id_is_propagated(client):
    r = client.get("/reservations", headers={"X-Correlation-ID": "abc-123"})
    assert r.headers["X-Correlation-ID"] == "abc-123"

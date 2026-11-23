import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    from app.main import app

    with TestClient(app) as c:
        yield c


EVENT = {
    "event_id": "e1",
    "event_type": "RESERVATION_CREATED",
    "timestamp": "2026-09-01T10:00:00Z",
    "correlation_id": "c1",
    "data": {"user_id": "u1", "vehicle_id": "v1"},
}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "history"


def test_record_event_appears_in_user_and_vehicle_history(client):
    service = client.app.state.history_service

    assert service.record_event(EVENT) is True

    r = client.get("/history/users/u1")
    assert r.status_code == 200
    assert [e["event_id"] for e in r.json()] == ["e1"]

    r = client.get("/history/vehicles/v1")
    assert r.status_code == 200
    assert [e["event_id"] for e in r.json()] == ["e1"]


def test_record_event_is_idempotent(client):
    service = client.app.state.history_service

    assert service.record_event(EVENT) is True
    assert service.record_event(EVENT) is False

    assert len(client.get("/history/users/u1").json()) == 1


def test_user_without_events_returns_empty_list(client):
    r = client.get("/history/users/nobody")
    assert r.status_code == 200
    assert r.json() == []

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("EVENTS_TOPIC_ARN", raising=False)
    from app.main import app

    with TestClient(app) as c:
        yield c


NEW_ORDER = {"vehicle_id": "S-001", "type": "CHARGE", "reason": "batería baja"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "maintenance"


def test_create_order(client):
    r = client.post("/orders", json=NEW_ORDER)
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "OPEN"
    assert order["vehicle_id"] == "S-001"


def test_duplicate_open_order_returns_409(client):
    assert client.post("/orders", json=NEW_ORDER).status_code == 201
    r = client.post("/orders", json=NEW_ORDER)
    assert r.status_code == 409


def test_withdraw_without_assign_returns_409(client):
    order_id = client.post("/orders", json=NEW_ORDER).json()["order_id"]
    r = client.post(f"/orders/{order_id}/withdraw")
    assert r.status_code == 409
    assert client.get(f"/orders/{order_id}").json()["status"] == "OPEN"


def test_full_flow_ends_completed(client):
    order_id = client.post("/orders", json=NEW_ORDER).json()["order_id"]

    for action, status in (
        ("assign", "ASSIGNED"),
        ("withdraw", "IN_PROGRESS"),
        ("complete", "COMPLETED"),
    ):
        r = client.post(f"/orders/{order_id}/{action}")
        assert r.status_code == 200
        assert r.json()["status"] == status

    assert client.get(f"/orders/{order_id}").json()["status"] == "COMPLETED"


def test_unknown_order_returns_404(client):
    assert client.get("/orders/M-000").status_code == 404

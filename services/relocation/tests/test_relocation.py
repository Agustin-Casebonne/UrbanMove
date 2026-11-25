import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("EVENTS_TOPIC_ARN", raising=False)
    from app.main import app

    with TestClient(app) as c:
        yield c


NEW_ORDER = {
    "from_zone": "Z1",
    "to_zone": "Z3",
    "vehicle_type": "BIKE",
    "quantity": 2,
    "reason": "déficit en Z3",
}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "relocation"


def test_create_order(client):
    r = client.post("/orders", json=NEW_ORDER)
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "OPEN"
    assert order["from_zone"] == "Z1"
    assert order["to_zone"] == "Z3"


def test_duplicate_open_order_returns_409(client):
    assert client.post("/orders", json=NEW_ORDER).status_code == 201
    r = client.post("/orders", json=NEW_ORDER)
    assert r.status_code == 409


def test_same_zones_returns_422(client):
    r = client.post("/orders", json={**NEW_ORDER, "to_zone": NEW_ORDER["from_zone"]})
    assert r.status_code == 422


def test_complete_without_start_returns_409(client):
    order_id = client.post("/orders", json=NEW_ORDER).json()["order_id"]
    r = client.post(f"/orders/{order_id}/complete", json={"vehicle_ids": ["B-001"]})
    assert r.status_code == 409
    assert client.get(f"/orders/{order_id}").json()["status"] == "OPEN"


def test_full_flow_ends_completed(client):
    order_id = client.post("/orders", json=NEW_ORDER).json()["order_id"]

    for action, status in (("assign", "ASSIGNED"), ("start", "IN_PROGRESS")):
        r = client.post(f"/orders/{order_id}/{action}")
        assert r.status_code == 200
        assert r.json()["status"] == status

    vehicle_ids = ["B-001", "B-002"]
    r = client.post(f"/orders/{order_id}/complete", json={"vehicle_ids": vehicle_ids})
    assert r.status_code == 200

    order = client.get(f"/orders/{order_id}").json()
    assert order["status"] == "COMPLETED"
    assert order["vehicle_ids"] == vehicle_ids
    assert order["completed_at"] is not None


def test_unknown_order_returns_404(client):
    assert client.get("/orders/RL-000").status_code == 404

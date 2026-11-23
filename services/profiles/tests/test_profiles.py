import uuid

from fastapi.testclient import TestClient

from app.main import app


def _new_id() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


def _create(client, user_id=None, name="Ana", email="ana@example.com"):
    user_id = user_id or _new_id()
    r = client.post("/profiles", json={"user_id": user_id, "name": name, "email": email})
    return user_id, r


def test_post_then_get_profile():
    with TestClient(app) as client:
        user_id, r = _create(client)
        assert r.status_code == 201
        g = client.get(f"/profiles/{user_id}")
    assert g.status_code == 200
    assert g.json()["user_id"] == user_id
    assert g.json()["name"] == "Ana"
    assert g.json()["email"] == "ana@example.com"
    assert g.json()["active"] is True


def test_get_unknown_profile_returns_404():
    with TestClient(app) as client:
        r = client.get(f"/profiles/{_new_id()}")
    assert r.status_code == 404


def test_put_updates_phone_and_vehicle():
    with TestClient(app) as client:
        user_id, _ = _create(client)
        r = client.put(
            f"/profiles/{user_id}",
            json={
                "name": "Ana B",
                "phone_number": "600123123",
                "preferred_vehicle_type": "SCOOTER",
            },
        )
        g = client.get(f"/profiles/{user_id}")
    assert r.status_code == 200
    assert g.json()["name"] == "Ana B"
    assert g.json()["phone_number"] == "600123123"
    assert g.json()["preferred_vehicle_type"] == "SCOOTER"


def test_delete_sets_active_false():
    with TestClient(app) as client:
        user_id, _ = _create(client)
        r = client.delete(f"/profiles/{user_id}")
        g = client.get(f"/profiles/{user_id}")
    assert r.status_code == 200
    assert r.json()["active"] is False
    assert g.json()["active"] is False


def test_invalid_email_returns_422():
    with TestClient(app) as client:
        _, r = _create(client, email="sin-arroba")
    assert r.status_code == 422


def test_empty_name_returns_422():
    with TestClient(app) as client:
        _, r = _create(client, name="  ")
    assert r.status_code == 422


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "profiles"


def test_user_registered_event_creates_profile_idempotently():
    with TestClient(app) as client:
        service = app.state.profiles_service
        data = {"user_id": "evt-user-1", "email": "ana@example.com", "role": "USER"}
        service.handle_event("UserRegistered", data)
        service.handle_event("UserRegistered", data)  # duplicado: no falla ni duplica
        service.handle_event("OtroEvento", {})  # se ignora
        r = client.get("/profiles/evt-user-1")
    assert r.status_code == 200
    assert r.json()["name"] == "ana"
    assert r.json()["email"] == "ana@example.com"

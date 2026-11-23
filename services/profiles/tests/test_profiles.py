from fastapi.testclient import TestClient

from app.main import app


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

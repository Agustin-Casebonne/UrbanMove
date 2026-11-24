"""Tests del dominio de identity con fakes en memoria.

No hay FastAPI, SQLite, bcrypt, JWT ni SNS: se prueba solo IdentityService.
Cada fake hereda de su puerto, así que si el puerto cambia, estos tests fallan.
"""

import pytest

from app.domain.model import (
    InvalidCredentials,
    InvalidToken,
    UserAlreadyExists,
    UserNotFound,
    UserRole,
    WeakPassword,
)
from app.ports.ports import EventPublisher, PasswordHasher, TokenIssuer, UserRepository
from app.service import IdentityService


class FakeUserRepository(UserRepository):
    def __init__(self):
        self.users = {}

    def ping(self):
        pass

    def save(self, user):
        self.users[user.user_id] = user

    def get_user(self, user_id):
        return self.users.get(user_id)

    def get_by_email(self, email):
        return next((u for u in self.users.values() if u.email == email), None)


class FakePasswordHasher(PasswordHasher):
    def hash_password(self, password):
        return f"hashed:{password}"

    def verify_password(self, password, password_hash):
        return password_hash == f"hashed:{password}"


class FakeTokenIssuer(TokenIssuer):
    def issue_token(self, user_id, role):
        return f"token:{user_id}:{role.value}"

    def validate_token(self, token):
        prefix, sep, rest = token.partition(":")
        if prefix != "token" or not sep:
            raise InvalidToken("Invalid token.")
        user_id, _, role = rest.partition(":")
        return {"user_id": user_id, "role": role}


class FakeEventPublisher(EventPublisher):
    def __init__(self):
        self.events = []

    def publish(self, event_type, data):
        self.events.append((event_type, data))


@pytest.fixture
def events():
    return FakeEventPublisher()


@pytest.fixture
def service(events):
    return IdentityService(FakeUserRepository(), FakeTokenIssuer(), FakePasswordHasher(), events)


def register(service, email="a@a.com", password="Abcdef123!", role=UserRole.USER):
    return service.register_user(email, password, role)


# --- register_user ---


def test_register_user_saves_user_with_hashed_password(service):
    user = register(service)

    assert user.email == "a@a.com"
    assert user.role == UserRole.USER
    assert user.password_hash == "hashed:Abcdef123!"
    assert service.get_user(user.user_id) == user


def test_register_user_publishes_event(service, events):
    user = register(service, role=UserRole.ADMIN)

    assert events.events == [
        ("UserRegistered", {"user_id": user.user_id, "email": "a@a.com", "role": "ADMIN"}),
    ]


def test_register_user_rejects_short_password(service, events):
    with pytest.raises(WeakPassword):
        register(service, password="corta")

    assert events.events == []


def test_register_user_rejects_duplicate_email(service, events):
    register(service)

    with pytest.raises(UserAlreadyExists):
        register(service)

    assert len(events.events) == 1


# --- get_user ---


def test_get_user_not_found(service):
    with pytest.raises(UserNotFound):
        service.get_user("no-existe")


# --- login ---


def test_login_returns_token_for_valid_credentials(service):
    user = register(service, role=UserRole.MAINTENANCE)

    token = service.login("a@a.com", "Abcdef123!")

    assert token == f"token:{user.user_id}:MAINTENANCE"


def test_login_rejects_wrong_password(service):
    register(service)

    with pytest.raises(InvalidCredentials):
        service.login("a@a.com", "otra-password")


def test_login_rejects_unknown_email(service):
    with pytest.raises(InvalidCredentials):
        service.login("nadie@a.com", "Abcdef123!")


# --- validate_token ---


def test_validate_token_returns_payload(service):
    user = register(service)
    token = service.login("a@a.com", "Abcdef123!")

    assert service.validate_token(token) == {"user_id": user.user_id, "role": "USER"}


def test_validate_token_rejects_invalid_token(service):
    with pytest.raises(InvalidToken):
        service.validate_token("basura")

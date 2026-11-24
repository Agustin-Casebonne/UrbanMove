"""Lógica de negocio de identity. Solo usa domain/model.py y ports/ports.py.

Ejemplo: services/inventory/app/service.py
"""

import uuid
from datetime import datetime, timezone

from .domain.model import InvalidCredentials, User, UserAlreadyExists, UserNotFound, WeakPassword


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IdentityService:
    def __init__(self, user_repository, token_issuer, password_hasher, event_publisher):
        self.user_repository = user_repository
        self.token_issuer = token_issuer
        self.password_hasher = password_hasher
        self.event_publisher = event_publisher

    def check_health(self):
        self.user_repository.ping()

    def get_user(self, user_id):
        user = self.user_repository.get_user(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user

    def register_user(self, email, password, role):
        """Da de alta un usuario nuevo. Si ya existía, lanza UserAlreadyExists."""
        if len(password) < 8:
            raise WeakPassword("Password does not meet security requirements.")

        existing = self.user_repository.get_by_email(email)
        if existing is not None:
            raise UserAlreadyExists(email)
        password_hash = self.password_hasher.hash_password(password)

        user = User(
            user_id=str(uuid.uuid4()),
            email=email,
            password_hash=password_hash,
            role=role,
            created_at=now_iso(),
        )
        self.user_repository.save(user)
        self.event_publisher.publish(
            "UserRegistered",
            {
                "user_id": user.user_id,
                "email": user.email,
                "role": user.role.value,
            },
        )
        return user

    def validate_token(self, token):
        """Valida un token y devuelve su payload. Lanza InvalidToken si no es válido."""
        return self.token_issuer.validate_token(token)

    def login(self, email, password):
        """Valida credenciales y devuelve un token. Lanza InvalidCredentials si no son válidas."""
        user = self.user_repository.get_by_email(email)
        if user is None:
            raise InvalidCredentials("Invalid email or password.")
        if not self.password_hasher.verify_password(password, user.password_hash):
            raise InvalidCredentials("Invalid email or password.")
        token = self.token_issuer.issue_token(user.user_id, user.role)
        return token

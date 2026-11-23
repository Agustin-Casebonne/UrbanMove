"""Modelo de dominio de identity: entidades, estados y reglas del negocio.

Ejemplo: services/inventory/app/domain/model.py
"""

from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    """Tipos de usuario."""

    USER = "USER"
    ADMIN = "ADMIN"
    MAINTENANCE = "MAINTENANCE"


class User(BaseModel):
    user_id: str
    email: str
    password_hash: str
    role: UserRole
    created_at: str


class UserAlreadyExists(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class InvalidToken(Exception):
    pass


class WeakPassword(Exception):
    pass


class UserNotFound(Exception):
    pass

"""Puertos de identity: contratos que el dominio necesita del exterior.

Los implementan los adaptadores de adapters/ y se conectan en main.py.
Ejemplo: services/inventory/app/ports/ports.py
"""

from abc import ABC, abstractmethod

from ..domain.model import User, UserRole


class UserRepository(ABC):
    """Repositorio de usuarios: dónde se guardan y cómo se buscan."""

    @abstractmethod
    def ping(self) -> None:
        """Comprueba que el repositorio funciona."""

    @abstractmethod
    def save(self, user: User) -> None:
        """Guarda un usuario en el repositorio."""

    @abstractmethod
    def get_user(self, user_id: str) -> User | None:
        """Busca un usuario por su id. Devuelve None si no existe."""

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Busca un usuario por su email. Devuelve None si no existe."""


class TokenIssuer(ABC):
    """Emite y valida tokens de autenticación."""

    @abstractmethod
    def issue_token(self, user_id: str, role: UserRole) -> str:
        """Emite un token para un usuario."""

    @abstractmethod
    def validate_token(self, token: str) -> dict:
        """Valida un token y devuelve su payload."""


class PasswordHasher(ABC):
    """Hashea y valida contraseñas."""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hashea una contraseña."""

    @abstractmethod
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verifica que una contraseña coincide con su hash."""


class EventPublisher(ABC):
    """Publica eventos de dominio."""

    @abstractmethod
    def publish(self, event_type: str, data: dict) -> None:
        """Publica un evento de dominio."""

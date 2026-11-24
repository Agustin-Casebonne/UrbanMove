"""Puertos de profiles: contratos que el dominio necesita del exterior.

Los implementan los adaptadores de adapters/ y se conectan en main.py.
Ejemplo: services/inventory/app/ports/ports.py
"""

from abc import ABC, abstractmethod

from ..domain.model import Profile


class ProfileRepository(ABC):
    """Repositorio de perfiles: define las operaciones que el dominio necesita del exterior."""

    @abstractmethod
    def ping(self) -> None:
        """Comprueba que la base de datos responde."""

    @abstractmethod
    def get_profile(self, user_id: str) -> Profile | None:
        """Obtiene un usuario por su ID."""

    @abstractmethod
    def save(self, profile: Profile) -> None:
        """Crea un nuevo perfil."""

    @abstractmethod
    def update(self, user: Profile) -> None:
        """Actualiza un perfil existente."""

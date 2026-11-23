"""Puertos de profiles: contratos que el dominio necesita del exterior.

Los implementan los adaptadores de adapters/ y se conectan en main.py.
Ejemplo: services/inventory/app/ports/ports.py
"""
from abc import ABC, abstractmethod

from ..domain.model import Profile


class ProfileRepository(ABC):
    """Repositorio de perfiles: define las operaciones que el dominio necesita del exterior."""

    @abstractmethod
    def get_profile(self, user_id: str) -> Profile:
        """Obtiene un usuario por su ID."""
        pass

    @abstractmethod
    def save(self, user: Profile) -> None:
        """Crea un nuevo perfil."""
        pass

    @abstractmethod
    def update(self, user: Profile) -> None:
        """Actualiza un perfil existente."""
        pass

    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        """Elimina un perfil por su ID."""
        pass
"""Puertos de history: contratos que el dominio necesita del exterior.

Los implementan los adaptadores de adapters/ y se conectan en main.py.
Ejemplo: services/inventory/app/ports/ports.py
"""

from abc import ABC, abstractmethod

from ..domain.model import HistoryEntry


class HistoryRepository(ABC):
    @abstractmethod
    def ping(self) -> None: ...

    @abstractmethod
    def save(self, entry: HistoryEntry) -> None: ...

    @abstractmethod
    def exists(self, event_id: str) -> bool: ...

    @abstractmethod
    def by_user(self, user_id: str) -> list[HistoryEntry]: ...

    @abstractmethod
    def by_vehicle(self, vehicle_id: str) -> list[HistoryEntry]: ...

"""Puertos de relocation: contratos que el dominio necesita del exterior.

Los implementan los adaptadores de adapters/ y se conectan en main.py.
Ejemplo: services/inventory/app/ports/ports.py
"""

from abc import ABC, abstractmethod

from ..domain.model import RelocationOrder, RelocationStatus


class RelocationOrderRepository(ABC):
    @abstractmethod
    def ping(self) -> None: ...

    @abstractmethod
    def save(self, order: RelocationOrder) -> None: ...

    @abstractmethod
    def get(self, order_id: str) -> RelocationOrder | None: ...

    @abstractmethod
    def list_orders(
        self, status: RelocationStatus | None = None, to_zone: str | None = None
    ) -> list[RelocationOrder]: ...

    @abstractmethod
    def transition(
        self, order_id: str, from_status: RelocationStatus, to_status: RelocationStatus, updated_at: str
    ) -> bool: ...

    @abstractmethod
    def complete(self, order_id: str, vehicle_ids: list[str], completed_at: str) -> bool: ...


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event_type: str, data: dict) -> None: ...

"""Puertos de maintenance: contratos que el dominio necesita del exterior.

Los implementan los adaptadores de adapters/ y se conectan en main.py.
Ejemplo: services/inventory/app/ports/ports.py
"""


from abc import ABC, abstractmethod

from ..domain.model import MaintenanceOrder, MaintenanceStatus


class MaintenanceOrderRepository(ABC):

    @abstractmethod
    def ping(self) -> None: ...

    @abstractmethod
    def save(self, order: MaintenanceOrder) -> None: ...

    @abstractmethod
    def get(self, order_id: str) -> MaintenanceOrder | None: ...

    @abstractmethod
    def list_orders(self, status: MaintenanceStatus | None = None, vehicle_id: str | None = None) -> list[MaintenanceOrder]: ...

    @abstractmethod
    def transition(self, order_id: str, from_status: MaintenanceStatus, to_status: MaintenanceStatus, updated_at: str) -> bool: ...


class EventPublisher(ABC):

    @abstractmethod
    def publish(self, event_type: str, data: dict) -> None: ...

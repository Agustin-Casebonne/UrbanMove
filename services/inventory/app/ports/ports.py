"""Puertos: contratos entre el dominio y el exterior.

El dominio solo conoce estas interfaces. Las implementaciones concretas
están en adapters/ y se conectan en main.py:
- VehicleRepository -> adapters/db.py (SQLite)
- EventPublisher    -> adapters/events.py (SNS)
"""

from abc import ABC, abstractmethod

from ..domain.model import AdminStatus, Vehicle


class VehicleRepository(ABC):
    @abstractmethod
    def ping(self) -> None: ...

    @abstractmethod
    def save(self, vehicle: Vehicle) -> None: ...

    @abstractmethod
    def get(self, vehicle_id: str) -> Vehicle | None: ...

    @abstractmethod
    def list_all(self) -> list[Vehicle]: ...

    @abstractmethod
    def update_admin_status(self, vehicle_id: str, admin_status: AdminStatus) -> bool:
        """Devuelve False si el vehículo no existe."""
        ...


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event_type: str, data: dict) -> None: ...

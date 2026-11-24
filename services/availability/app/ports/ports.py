"""Puertos de availability: contratos que el dominio necesita del exterior.

Los implementan los adaptadores de adapters/ y se conectan en main.py.
Ejemplo: services/inventory/app/ports/ports.py
"""

from abc import ABC, abstractmethod

from ..domain.model import Vehicle, VehicleStatus, VehicleType


class VehicleRepository(ABC):
    @abstractmethod
    def ping(self) -> None: ...

    @abstractmethod
    def save(self, vehicle: Vehicle) -> None: ...

    @abstractmethod
    def get(self, vehicle_id: str) -> Vehicle | None: ...

    @abstractmethod
    def list_vehicles(
        self,
        zone_id: str | None = None,
        vehicle_type: VehicleType | None = None,
        status: VehicleStatus | None = None,
    ) -> list[Vehicle]: ...

    @abstractmethod
    def is_event_processed(self, event_id: str) -> bool: ...

    @abstractmethod
    def mark_event_processed(self, event_id: str, processed_at: str) -> None: ...


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event_type: str, data: dict) -> None: ...

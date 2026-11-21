"""Puertos de availability: contratos que el dominio necesita del exterior.

Los implementan los adaptadores de adapters/ y se conectan en main.py.
Ejemplo: services/inventory/app/ports/ports.py
"""

from abc import ABC, abstractmethod


class VehicleRepository(ABC):
    @abstractmethod
    def ping(self): ...

    @abstractmethod
    def save(self, vehicle): ...

    @abstractmethod
    def get(self, vehicle_id): ...

    @abstractmethod
    def list_vehicles(self, zone_id=None, vehicle_type=None, status=None): ...

    @abstractmethod
    def is_event_processed(self, event_id): ...

    @abstractmethod
    def mark_event_processed(self, event_id, processed_at): ...


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event_type, data): ...

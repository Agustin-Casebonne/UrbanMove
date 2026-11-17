"""Puertos de availability: contratos que el dominio necesita del exterior.

Los implementan los adaptadores de adapters/ y se conectan en main.py.
Ejemplo: services/inventory/app/ports/ports.py
"""
from typing import Protocol


class VehicleRepository(Protocol):
    def ping(self): ...

    def save(self, vehicle): ...

    def get(self, vehicle_id): ...

    def list_vehicles(self, zone_id=None, vehicle_type=None, status=None): ...

    def is_event_processed(self, event_id): ...

    def mark_event_processed(self, event_id, processed_at): ...


class EventPublisher(Protocol):
    def publish(self, event_type, data): ...
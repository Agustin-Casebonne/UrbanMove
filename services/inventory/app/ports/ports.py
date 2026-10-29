"""Puertos: contratos entre el dominio y el exterior.

El dominio solo conoce estas interfaces. Las implementaciones concretas
están en adapters/ y se conectan en main.py:
- VehicleRepository -> adapters/db.py (SQLite)
- EventPublisher    -> adapters/events.py (SNS)
"""

from typing import Protocol

from ..domain.model import AdminStatus, Vehicle


class VehicleRepository(Protocol):
    def ping(self) -> None: ...

    def save(self, vehicle: Vehicle) -> None: ...

    def get(self, vehicle_id: str) -> Vehicle | None: ...

    def list_all(self) -> list[Vehicle]: ...

    def update_admin_status(self, vehicle_id: str, admin_status: AdminStatus) -> bool:
        """Devuelve False si el vehículo no existe."""
        ...


class EventPublisher(Protocol):
    def publish(self, event_type: str, data: dict) -> None: ...

"""Lógica de negocio del inventario.

Solo depende del modelo y de los puertos: no sabe que existen FastAPI,
SQLite ni SNS.
"""

import uuid
from datetime import date, datetime, timezone

from ..ports.ports import EventPublisher, VehicleRepository
from .model import AdminStatus, Vehicle, VehicleNotFound, VehicleType


class InventoryService:
    def __init__(self, repository: VehicleRepository, publisher: EventPublisher):
        self.repository = repository
        self.publisher = publisher

    def check_health(self) -> None:
        self.repository.ping()

    def register_vehicle(
        self, vehicle_type: VehicleType, model: str, purchase_date: date, initial_zone: str
    ) -> Vehicle:
        vehicle = Vehicle(
            vehicle_type=vehicle_type,
            model=model,
            purchase_date=purchase_date,
            initial_zone=initial_zone,
            vehicle_id=f"{vehicle_type.value[0]}-{uuid.uuid4().hex[:8]}",
            admin_status=AdminStatus.ACTIVE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.repository.save(vehicle)  # primero se guarda, después se publica
        self.publisher.publish("VehiclePurchased", vehicle.model_dump(mode="json"))
        return vehicle

    def list_vehicles(self) -> list[Vehicle]:
        return self.repository.list_all()

    def get_vehicle(self, vehicle_id: str) -> Vehicle:
        vehicle = self.repository.get(vehicle_id)
        if vehicle is None:
            raise VehicleNotFound(vehicle_id)
        return vehicle

    def change_admin_status(self, vehicle_id: str, admin_status: AdminStatus) -> Vehicle:
        if not self.repository.update_admin_status(vehicle_id, admin_status):
            raise VehicleNotFound(vehicle_id)
        return self.get_vehicle(vehicle_id)

"""Lógica de negocio de maintenance.

Solo depende del modelo y de los puertos: no sabe que existen FastAPI,
SQLite ni SNS.

Ciclo de vida de una orden:  OPEN -> ASSIGNED -> IN_PROGRESS -> COMPLETED

- start_order retira el vehículo de la calle (VehicleWithdrawnForMaintenance).
- complete_order lo devuelve al servicio (VehicleReturnedToService).
- Repetir una transición ya hecha devuelve la orden sin publicar otro evento.
- handle_event crea una orden de recarga al recibir VehicleBatteryLow; si el
  vehículo ya tiene una orden abierta, no hace nada (idempotencia).
"""

import uuid
from datetime import datetime, timezone

from .domain.model import (
    InvalidTransition,
    MaintenanceOrder,
    MaintenanceOrderNotFound,
    MaintenanceStatus,
    MaintenanceType,
    OrderAlreadyOpen,
)
from .ports.ports import EventPublisher, MaintenanceOrderRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


class MaintenanceService:
    def __init__(self, repository: MaintenanceOrderRepository, publisher: EventPublisher):
        self.repository = repository
        self.publisher = publisher

    def check_health(self) -> None:
        self.repository.ping()

    def get_order(self, order_id: str) -> MaintenanceOrder:
        order = self.repository.get(order_id)
        if order is None:
            raise MaintenanceOrderNotFound(order_id)
        return order

    def list_orders(
        self, status: MaintenanceStatus | None = None, vehicle_id: str | None = None
    ) -> list[MaintenanceOrder]:
        return self.repository.list_orders(status=status, vehicle_id=vehicle_id)

    def create_order(self, vehicle_id: str, type: MaintenanceType, reason: str) -> MaintenanceOrder:
        now = to_iso(utc_now())
        order = MaintenanceOrder(
            order_id=f"M-{uuid.uuid4().hex[:12]}",
            vehicle_id=vehicle_id,
            type=type,
            status=MaintenanceStatus.OPEN,
            reason=reason,
            created_at=now,
            updated_at=now,
        )
        self.repository.save(order)
        return order

    def assign_order(self, order_id: str) -> MaintenanceOrder:
        order, _ = self._transition(order_id, MaintenanceStatus.OPEN, MaintenanceStatus.ASSIGNED, "asignar")
        return order

    def start_order(self, order_id: str) -> MaintenanceOrder:
        order, changed = self._transition(
            order_id, MaintenanceStatus.ASSIGNED, MaintenanceStatus.IN_PROGRESS, "iniciar"
        )
        if changed:  # primero se guarda, después se publica
            self.publisher.publish("VehicleWithdrawnForMaintenance", self._event_data(order))
        return order

    def complete_order(self, order_id: str) -> MaintenanceOrder:
        order, changed = self._transition(
            order_id, MaintenanceStatus.IN_PROGRESS, MaintenanceStatus.COMPLETED, "completar"
        )
        if changed:
            self.publisher.publish("VehicleReturnedToService", self._event_data(order))
        return order

    def handle_event(self, event: dict) -> None:
        if event.get("event_type") != "VehicleBatteryLow":
            return
        vehicle_id = event["data"]["vehicle_id"]
        try:
            self.create_order(vehicle_id, MaintenanceType.CHARGE, "batería baja")
        except OrderAlreadyOpen:
            pass

    def _transition(
        self, order_id: str, from_status: MaintenanceStatus, to_status: MaintenanceStatus, action: str
    ) -> tuple[MaintenanceOrder, bool]:
        """Devuelve (orden, True si ha cambiado ahora, False si ya estaba en to_status)."""
        order = self.get_order(order_id)
        if order.status == to_status:
            return order, False
        if not self.repository.transition(order_id, from_status, to_status, to_iso(utc_now())):
            raise InvalidTransition(order_id, order.status, action)
        return self.get_order(order_id), True

    @staticmethod
    def _event_data(order: MaintenanceOrder) -> dict:
        return {"order_id": order.order_id, "vehicle_id": order.vehicle_id, "type": order.type.value}

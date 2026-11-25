"""Lógica de negocio de relocation.

Solo depende del modelo y de los puertos: no sabe que existen FastAPI,
SQLite ni SNS.

Ciclo de vida de una orden:  OPEN -> ASSIGNED -> IN_PROGRESS -> COMPLETED

- create_order publica RelocationOrderCreated; si ya hay una orden abierta para
  el mismo trayecto y tipo de vehículo, lanza OrderAlreadyOpen.
- assign_order y start_order no publican eventos: no cambian el estado de
  ningún vehículo.
- complete_order publica RelocationOrderCompleted con los vehículos movidos.
- Repetir una transición ya hecha devuelve la orden sin publicar otro evento.
"""

import uuid
from datetime import datetime, timezone

from .domain.model import (
    InvalidTransition,
    RelocationOrder,
    RelocationOrderNotFound,
    RelocationStatus,
    VehicleType,
)
from .ports.ports import EventPublisher, RelocationOrderRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


class RelocationService:
    def __init__(self, repository: RelocationOrderRepository, publisher: EventPublisher):
        self.repository = repository
        self.publisher = publisher

    def check_health(self) -> None:
        self.repository.ping()

    def get_order(self, order_id: str) -> RelocationOrder:
        order = self.repository.get(order_id)
        if order is None:
            raise RelocationOrderNotFound(order_id)
        return order

    def list_orders(
        self, status: RelocationStatus | None = None, to_zone: str | None = None
    ) -> list[RelocationOrder]:
        return self.repository.list_orders(status=status, to_zone=to_zone)

    def create_order(
        self, from_zone: str, to_zone: str, vehicle_type: VehicleType, quantity: int, reason: str
    ) -> RelocationOrder:
        now = to_iso(utc_now())
        order = RelocationOrder(
            order_id=f"RL-{uuid.uuid4().hex[:12]}",
            from_zone=from_zone,
            to_zone=to_zone,
            vehicle_type=vehicle_type,
            quantity=quantity,
            reason=reason,
            status=RelocationStatus.OPEN,
            created_at=now,
            updated_at=now,
        )
        self.repository.save(order)
        self.publisher.publish(
            "RelocationOrderCreated",
            {
                "order_id": order.order_id,
                "from_zone": order.from_zone,
                "to_zone": order.to_zone,
                "vehicle_type": order.vehicle_type.value,
                "quantity": order.quantity,
            },
        )
        return order

    def assign_order(self, order_id: str) -> RelocationOrder:
        return self._transition(order_id, RelocationStatus.OPEN, RelocationStatus.ASSIGNED, "asignar")

    def start_order(self, order_id: str) -> RelocationOrder:
        return self._transition(order_id, RelocationStatus.ASSIGNED, RelocationStatus.IN_PROGRESS, "iniciar")

    def complete_order(self, order_id: str, vehicle_ids: list[str]) -> RelocationOrder:
        order = self.get_order(order_id)
        if order.status == RelocationStatus.COMPLETED:
            return order
        now = to_iso(utc_now())
        if not self.repository.complete(order_id, vehicle_ids, now):
            raise InvalidTransition(order_id, order.status, "completar")
        delay_min = round((utc_now() - datetime.fromisoformat(order.created_at)).total_seconds() / 60, 1)
        self.publisher.publish(
            "RelocationOrderCompleted",
            {
                "order_id": order.order_id,
                "from_zone": order.from_zone,
                "to_zone": order.to_zone,
                "vehicle_ids": vehicle_ids,
                "delay_min": delay_min,
            },
        )
        return self.get_order(order_id)

    def _transition(
        self, order_id: str, from_status: RelocationStatus, to_status: RelocationStatus, action: str
    ) -> RelocationOrder:
        """Si la orden ya está en to_status, la devuelve sin cambiar nada."""
        order = self.get_order(order_id)
        if order.status == to_status:
            return order
        if not self.repository.transition(order_id, from_status, to_status, to_iso(utc_now())):
            raise InvalidTransition(order_id, order.status, action)
        return self.get_order(order_id)

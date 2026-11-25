"""Adaptador de entrada: endpoints REST de maintenance.

Solo traduce HTTP <-> dominio. La lógica está en service.py.

Códigos de respuesta:
- 201 orden creada
- 404 orden no encontrada
- 409 conflicto: el vehículo ya tiene una orden abierta o la acción no está
      permitida en el estado actual de la orden
- 422 datos de entrada inválidos (lo genera FastAPI)
- 503 la base de datos no responde
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .domain.model import (
    InvalidTransition,
    MaintenanceOrder,
    MaintenanceOrderNotFound,
    MaintenanceStatus,
    MaintenanceType,
    OrderAlreadyOpen,
)
from .service import MaintenanceService

SERVICE_NAME = "maintenance"

router = APIRouter()


class OrderIn(BaseModel):
    vehicle_id: str
    type: MaintenanceType
    reason: str


@router.get("/health")
def health(request: Request):
    service: MaintenanceService = request.app.state.maintenance_service
    try:
        service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Orden de mantenimiento no encontrada")


@router.post("/orders", response_model=MaintenanceOrder, status_code=201)
def create_order(body: OrderIn, request: Request):
    """Crea una orden. También la llama la Lambda maintenance_detector.

    Si el vehículo ya tiene una orden abierta responde 409 (la Lambda lo
    trata como "ya estaba hecho": idempotencia).
    """
    service: MaintenanceService = request.app.state.maintenance_service
    try:
        return service.create_order(body.vehicle_id, body.type, body.reason)
    except OrderAlreadyOpen as exc:
        raise HTTPException(status_code=409, detail="El vehículo ya tiene una orden abierta") from exc


@router.get("/orders", response_model=list[MaintenanceOrder])
def list_orders(
    request: Request,
    status: MaintenanceStatus | None = None,
    vehicle_id: str | None = None,
):
    service: MaintenanceService = request.app.state.maintenance_service
    return service.list_orders(status=status, vehicle_id=vehicle_id)


@router.get("/orders/{order_id}", response_model=MaintenanceOrder)
def get_order(order_id: str, request: Request):
    service: MaintenanceService = request.app.state.maintenance_service
    try:
        return service.get_order(order_id)
    except MaintenanceOrderNotFound as exc:
        raise _not_found() from exc


@router.post("/orders/{order_id}/assign", response_model=MaintenanceOrder)
def assign_order(order_id: str, request: Request):
    service: MaintenanceService = request.app.state.maintenance_service
    try:
        return service.assign_order(order_id)
    except MaintenanceOrderNotFound as exc:
        raise _not_found() from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/orders/{order_id}/withdraw", response_model=MaintenanceOrder)
def withdraw_order(order_id: str, request: Request):
    """Retira el vehículo de la calle. Publica VehicleWithdrawnForMaintenance."""
    service: MaintenanceService = request.app.state.maintenance_service
    try:
        return service.start_order(order_id)
    except MaintenanceOrderNotFound as exc:
        raise _not_found() from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/orders/{order_id}/complete", response_model=MaintenanceOrder)
def complete_order(order_id: str, request: Request):
    """Devuelve el vehículo al servicio. Publica VehicleReturnedToService."""
    service: MaintenanceService = request.app.state.maintenance_service
    try:
        return service.complete_order(order_id)
    except MaintenanceOrderNotFound as exc:
        raise _not_found() from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
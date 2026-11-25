"""Adaptador de entrada: endpoints REST de relocation.

Solo traduce HTTP <-> dominio. La lógica está en service.py.

Códigos de respuesta:
- 201 orden creada
- 404 orden no encontrada
- 409 conflicto: ya hay una orden abierta para ese trayecto y tipo de vehículo
      o la acción no está permitida en el estado actual de la orden
- 422 datos de entrada inválidos (lo genera FastAPI)
- 503 la base de datos no responde
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from .domain.model import (
    InvalidTransition,
    OrderAlreadyOpen,
    RelocationOrder,
    RelocationOrderNotFound,
    RelocationStatus,
    VehicleType,
)
from .service import RelocationService

SERVICE_NAME = "relocation"

router = APIRouter()


class RelocationOrderIn(BaseModel):
    from_zone: str
    to_zone: str
    vehicle_type: VehicleType
    quantity: int = Field(gt=0)
    reason: str

    @model_validator(mode="after")
    def check_zones_differ(self):
        if self.from_zone == self.to_zone:
            raise ValueError("from_zone y to_zone deben ser distintas")
        return self


class CompleteIn(BaseModel):
    vehicle_ids: list[str] = Field(min_length=1)


@router.get("/health")
def health(request: Request):
    service: RelocationService = request.app.state.relocation_service
    try:
        service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Orden de recolocación no encontrada")


@router.post("/orders", response_model=RelocationOrder, status_code=201)
def create_order(body: RelocationOrderIn, request: Request):
    """Crea una orden. También la llama la Lambda de recolocación.

    Si ya hay una orden abierta para ese trayecto y tipo de vehículo responde
    409 (la Lambda lo trata como "ya estaba hecho": idempotencia).
    """
    try:
        return request.app.state.relocation_service.create_order(
            body.from_zone, body.to_zone, body.vehicle_type, body.quantity, body.reason
        )
    except OrderAlreadyOpen as exc:
        raise HTTPException(
            status_code=409, detail="Ya hay una orden abierta para ese trayecto y tipo de vehículo"
        ) from exc


@router.get("/orders", response_model=list[RelocationOrder])
def list_orders(
    request: Request,
    status: RelocationStatus | None = None,
    to_zone: str | None = None,
):
    return request.app.state.relocation_service.list_orders(status=status, to_zone=to_zone)


@router.get("/orders/{order_id}", response_model=RelocationOrder)
def get_order(order_id: str, request: Request):
    service: RelocationService = request.app.state.relocation_service
    try:
        return service.get_order(order_id)
    except RelocationOrderNotFound as exc:
        raise _not_found() from exc


@router.post("/orders/{order_id}/assign", response_model=RelocationOrder)
def assign_order(order_id: str, request: Request):
    try:
        return request.app.state.relocation_service.assign_order(order_id)
    except RelocationOrderNotFound as exc:
        raise _not_found() from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/orders/{order_id}/start", response_model=RelocationOrder)
def start_order(order_id: str, request: Request):
    try:
        return request.app.state.relocation_service.start_order(order_id)
    except RelocationOrderNotFound as exc:
        raise _not_found() from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/orders/{order_id}/complete", response_model=RelocationOrder)
def complete_order(order_id: str, body: CompleteIn, request: Request):
    """Completa la orden. Publica RelocationOrderCompleted."""
    try:
        return request.app.state.relocation_service.complete_order(order_id, body.vehicle_ids)
    except RelocationOrderNotFound as exc:
        raise _not_found() from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

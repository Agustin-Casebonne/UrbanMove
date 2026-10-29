"""Adaptador de entrada: endpoints REST del inventario.

Solo traduce HTTP <-> dominio (JSON, códigos 201/404/503). La lógica está
en domain/service.py.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..domain.model import AdminStatus, Vehicle, VehicleNotFound, VehicleType
from ..domain.service import InventoryService

SERVICE_NAME = "inventory"

router = APIRouter()


class VehicleIn(BaseModel):
    vehicle_type: VehicleType
    model: str
    purchase_date: date
    initial_zone: str


class AdminStatusIn(BaseModel):
    admin_status: AdminStatus


def get_service(request: Request) -> InventoryService:
    """El servicio lo crea main.py al arrancar."""
    return request.app.state.inventory_service


@router.get("/health")
def health(service: InventoryService = Depends(get_service)):
    try:
        service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


@router.post("/vehicles", response_model=Vehicle, status_code=201)
def create_vehicle(body: VehicleIn, service: InventoryService = Depends(get_service)):
    return service.register_vehicle(body.vehicle_type, body.model, body.purchase_date, body.initial_zone)


@router.get("/vehicles", response_model=list[Vehicle])
def list_vehicles(service: InventoryService = Depends(get_service)):
    return service.list_vehicles()


@router.get("/vehicles/{vehicle_id}", response_model=Vehicle)
def get_vehicle(vehicle_id: str, service: InventoryService = Depends(get_service)):
    try:
        return service.get_vehicle(vehicle_id)
    except VehicleNotFound as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc


@router.patch("/vehicles/{vehicle_id}/admin-status", response_model=Vehicle)
def update_admin_status(
    vehicle_id: str, body: AdminStatusIn, service: InventoryService = Depends(get_service)
):
    try:
        return service.change_admin_status(vehicle_id, body.admin_status)
    except VehicleNotFound as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc

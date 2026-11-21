"""Adaptador de entrada: endpoints REST de availability.

Solo traduce HTTP <-> dominio. La lógica va en domain/service.py.
Ejemplo completo: services/inventory/app/adapters/api.py
"""

from fastapi import APIRouter, HTTPException, Request

from ..domain.model import InvalidTransition, Vehicle, VehicleNotFound, VehicleStatus

SERVICE_NAME = "availability"

router = APIRouter()


@router.get("/health")
def health(request: Request):
    """Comprueba que el servicio responde y que la base de datos está viva."""
    service = request.app.state.availability_service
    try:
        service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


def get_service(request: Request):
    """Devuelve el servicio que creó main.py al arrancar."""
    return request.app.state.availability_service


@router.get("/vehicles/{vehicle_id}", response_model=Vehicle)
def get_vehicle(vehicle_id: str, request: Request):
    """Devuelve el estado de un vehículo."""
    service = request.app.state.availability_service
    try:
        return service.get_vehicle(vehicle_id)
    except VehicleNotFound as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc


@router.get("/availability", response_model=list[Vehicle])
def list_vehicles(request: Request, zone_id=None, vehicle_type=None, status=None):
    """Lista los vehículos que cumplen los filtros."""
    service = request.app.state.availability_service
    return service.list_vehicles(zone_id=zone_id, vehicle_type=vehicle_type, status=status)


@router.post("/vehicles/{vehicle_id}/transition", response_model=Vehicle)
def transition(
    vehicle_id: str,
    status: VehicleStatus,
    request: Request,
    zone_id: str | None = None,
    battery_level: int | None = None,
):
    service = request.app.state.availability_service
    try:
        return service.transition(vehicle_id, status, zone_id=zone_id, battery_level=battery_level)
    except VehicleNotFound as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/vehicles/{vehicle_id}/battery", response_model=Vehicle)
def report_battery(vehicle_id: str, battery_level: int, request: Request):
    service = request.app.state.availability_service
    try:
        return service.report_battery(vehicle_id, battery_level)
    except VehicleNotFound as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc

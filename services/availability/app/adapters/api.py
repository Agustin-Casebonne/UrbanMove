"""Adaptador de entrada: endpoints REST de availability.

Solo traduce HTTP <-> dominio. La lógica va en domain/service.py.
Ejemplo completo: services/inventory/app/adapters/api.py
"""

from fastapi import APIRouter, Request

from ..domain.model import Vehicle, VehicleStatus

SERVICE_NAME = "availability"

router = APIRouter()


@router.get("/health")
def health(request: Request):
    """Comprueba que el servicio responde y que la base de datos está viva."""
    service = request.app.state.availability_service
    try:
        service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception:
        return {"status": "error", "service": SERVICE_NAME}


def get_service(request: Request):
    """Devuelve el servicio que creó main.py al arrancar."""
    return request.app.state.availability_service


@router.get("/vehicles/{vehicle_id}", response_model=Vehicle)
def get_vehicle(vehicle_id: str, request: Request):
    """Devuelve el estado de un vehículo."""
    service = request.app.state.availability_service
    return service.get_vehicle(vehicle_id)


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
    return service.transition(vehicle_id, status, zone_id=zone_id, battery_level=battery_level)


@router.post("/vehicles/{vehicle_id}/battery", response_model=Vehicle)
def report_battery(vehicle_id: str, battery_level: int, request: Request):
    service = request.app.state.availability_service
    return service.report_battery(vehicle_id, battery_level)

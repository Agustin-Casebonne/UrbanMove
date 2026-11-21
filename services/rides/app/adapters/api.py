"""Adaptador de entrada: endpoints REST de rides.

Solo traduce HTTP <-> dominio. La lógica va en domain/service.py.
Ejemplo completo: services/inventory/app/adapters/api.py
"""

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from ..domain.model import Ride, RideNotFound, RideStatus, RideAlreadyFinished, VehicleNotAvailable, AvailabilityServiceDown

SERVICE_NAME = "rides"

router = APIRouter()


@router.get("/health")
def health(request: Request):
    service = request.app.state.ride_service
    try:
        service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


@router.get("/rides/{ride_id}")
def get_ride(ride_id: str, request: Request):
    ride_service = request.app.state.ride_service
    return ride_service.get_ride(ride_id=ride_id)


@router.post("/rides/start")
def start_ride(
    request: Request, user_id: str, vehicle_id: str, origin_zone: str, reservation_id: str | None = None
):
    ride_service = request.app.state.ride_service
    ride = ride_service.start_ride(
        user_id=user_id, vehicle_id=vehicle_id, origin_zone=origin_zone, reservation_id=reservation_id
    )
    return ride


@router.post("/rides/{ride_id}/finish")
def finish_ride(ride_id: str, request: Request, destination_zone: str, battery_level: int | None = None):
    ride_service = request.app.state.ride_service
    ride = ride_service.finish_ride(
        ride_id=ride_id, destination_zone=destination_zone, battery_level=battery_level
    )
    return ride


@router.get("/rides", response_model=list[Ride])
def list_rides(user_id: str, request: Request, status: RideStatus | None = None):
    ride_service = request.app.state.ride_service
    rides = ride_service.list_rides(user_id=user_id, status=status)
    return rides


# Traducción de errores de dominio a HTTP, en un único sitio.
ERROR_STATUS = {
    RideNotFound: (404, "Viaje no encontrado"),
    RideAlreadyFinished: (409, "El viaje ya ha finalizado"),
    VehicleNotAvailable: (409, None),  # usa el mensaje de la excepción
    AvailabilityServiceDown: (503, "Servicio de disponibilidad no disponible, inténtalo más tarde"),
}


def register_error_handlers(app: FastAPI) -> None:
    for exc_class, (status_code, message) in ERROR_STATUS.items():

        def handler(request: Request, exc: Exception, status_code=status_code, message=message):
            return JSONResponse(status_code=status_code, content={"detail": message or str(exc)})

        app.add_exception_handler(exc_class, handler)

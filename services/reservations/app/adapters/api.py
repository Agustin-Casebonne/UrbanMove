"""Adaptador de entrada: endpoints REST de reservations.

Solo traduce HTTP <-> dominio. La lógica está en domain/service.py.

Códigos de respuesta:
- 201 reserva creada
- 404 reserva o vehículo no encontrado
- 409 conflicto: vehículo ya reservado, usuario con otra reserva activa,
      vehículo no disponible o acción no permitida en el estado actual
- 422 datos de entrada inválidos (lo genera FastAPI)
- 503 la base de datos o el servicio availability no responden
"""

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..domain.model import (
    AvailabilityServiceDown,
    InvalidTransition,
    Reservation,
    ReservationNotFound,
    ReservationNotYetExpired,
    ReservationStatus,
    UserAlreadyHasReservation,
    VehicleAlreadyReserved,
    VehicleNotAvailable,
    VehicleNotFound,
    VehicleType,
)
from ..domain.service import ReservationService

SERVICE_NAME = "reservations"

router = APIRouter()


class ReservationIn(BaseModel):
    user_id: str
    vehicle_id: str
    vehicle_type: VehicleType
    zone_id: str


def get_service(request: Request) -> ReservationService:
    """El servicio lo crea main.py al arrancar."""
    return request.app.state.reservation_service


@router.get("/health")
def health(service: ReservationService = Depends(get_service)):
    try:
        service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


@router.post("/reservations", response_model=Reservation, status_code=201)
def create_reservation(body: ReservationIn, service: ReservationService = Depends(get_service)):
    return service.create_reservation(body.user_id, body.vehicle_id, body.vehicle_type, body.zone_id)


@router.get("/reservations", response_model=list[Reservation])
def list_reservations(
    user_id: str | None = None,
    status: ReservationStatus | None = None,
    service: ReservationService = Depends(get_service),
):
    return service.list_reservations(user_id=user_id, status=status)


@router.post("/reservations/expire-overdue", response_model=list[Reservation])
def expire_overdue(service: ReservationService = Depends(get_service)):
    """Expira todas las reservas vencidas. Lo llama la Lambda de expiración."""
    return service.expire_overdue()


@router.get("/reservations/{reservation_id}", response_model=Reservation)
def get_reservation(reservation_id: str, service: ReservationService = Depends(get_service)):
    return service.get_reservation(reservation_id)


@router.post("/reservations/{reservation_id}/confirm", response_model=Reservation)
def confirm_reservation(reservation_id: str, service: ReservationService = Depends(get_service)):
    return service.confirm(reservation_id)


@router.post("/reservations/{reservation_id}/cancel", response_model=Reservation)
def cancel_reservation(reservation_id: str, service: ReservationService = Depends(get_service)):
    return service.cancel(reservation_id)


@router.post("/reservations/{reservation_id}/expire", response_model=Reservation)
def expire_reservation(reservation_id: str, service: ReservationService = Depends(get_service)):
    return service.expire(reservation_id)


@router.post("/reservations/{reservation_id}/fulfill", response_model=Reservation)
def fulfill_reservation(reservation_id: str, service: ReservationService = Depends(get_service)):
    """Marca la reserva como usada. Lo llama rides al iniciar el viaje."""
    return service.fulfill(reservation_id)


# Traducción de errores de dominio a HTTP, en un único sitio.
ERROR_STATUS = {
    ReservationNotFound: (404, "Reserva no encontrada"),
    VehicleNotFound: (404, "Vehículo no encontrado"),
    VehicleAlreadyReserved: (409, "El vehículo ya tiene una reserva activa"),
    UserAlreadyHasReservation: (409, "El usuario ya tiene una reserva activa"),
    VehicleNotAvailable: (409, "El vehículo no está disponible"),
    ReservationNotYetExpired: (409, "La reserva todavía no ha caducado"),
    InvalidTransition: (409, None),  # usa el mensaje de la excepción
    AvailabilityServiceDown: (503, "Servicio de disponibilidad no disponible, inténtalo más tarde"),
}


def register_error_handlers(app: FastAPI) -> None:
    for exc_class, (status_code, message) in ERROR_STATUS.items():

        def handler(request: Request, exc: Exception, status_code=status_code, message=message):
            return JSONResponse(status_code=status_code, content={"detail": message or str(exc)})

        app.add_exception_handler(exc_class, handler)

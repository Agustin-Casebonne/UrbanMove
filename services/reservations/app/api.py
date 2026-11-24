"""Adaptador de entrada: endpoints REST de reservations.

Solo traduce HTTP <-> dominio. La lógica está en service.py.

Códigos de respuesta:
- 201 reserva creada
- 404 reserva o vehículo no encontrado
- 409 conflicto: vehículo ya reservado, usuario con otra reserva activa,
      vehículo no disponible o acción no permitida en el estado actual
- 422 datos de entrada inválidos (lo genera FastAPI)
- 503 la base de datos o el servicio availability no responden
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .domain.model import (
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
from .service import ReservationService

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


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=503, detail="Servicio de disponibilidad no disponible, inténtalo más tarde"
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Reserva no encontrada")


@router.post("/reservations", response_model=Reservation, status_code=201)
def create_reservation(body: ReservationIn, service: ReservationService = Depends(get_service)):
    try:
        return service.create_reservation(body.user_id, body.vehicle_id, body.vehicle_type, body.zone_id)
    except VehicleNotFound as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc
    except VehicleAlreadyReserved as exc:
        raise HTTPException(status_code=409, detail="El vehículo ya tiene una reserva activa") from exc
    except UserAlreadyHasReservation as exc:
        raise HTTPException(status_code=409, detail="El usuario ya tiene una reserva activa") from exc
    except VehicleNotAvailable as exc:
        raise HTTPException(status_code=409, detail="El vehículo no está disponible") from exc
    except AvailabilityServiceDown as exc:
        raise _unavailable() from exc


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
    try:
        return service.get_reservation(reservation_id)
    except ReservationNotFound as exc:
        raise _not_found() from exc


@router.post("/reservations/{reservation_id}/confirm", response_model=Reservation)
def confirm_reservation(reservation_id: str, service: ReservationService = Depends(get_service)):
    try:
        return service.confirm(reservation_id)
    except ReservationNotFound as exc:
        raise _not_found() from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/reservations/{reservation_id}/cancel", response_model=Reservation)
def cancel_reservation(reservation_id: str, service: ReservationService = Depends(get_service)):
    try:
        return service.cancel(reservation_id)
    except ReservationNotFound as exc:
        raise _not_found() from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/reservations/{reservation_id}/expire", response_model=Reservation)
def expire_reservation(reservation_id: str, service: ReservationService = Depends(get_service)):
    try:
        return service.expire(reservation_id)
    except ReservationNotFound as exc:
        raise _not_found() from exc
    except ReservationNotYetExpired as exc:
        raise HTTPException(status_code=409, detail="La reserva todavía no ha caducado") from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/reservations/{reservation_id}/fulfill", response_model=Reservation)
def fulfill_reservation(reservation_id: str, service: ReservationService = Depends(get_service)):
    """Marca la reserva como usada. Lo llama rides al iniciar el viaje."""
    try:
        return service.fulfill(reservation_id)
    except ReservationNotFound as exc:
        raise _not_found() from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

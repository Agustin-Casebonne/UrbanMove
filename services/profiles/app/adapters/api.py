"""Adaptador de entrada: endpoints REST de profiles.

Solo traduce HTTP <-> dominio. La lógica va en domain/service.py.
Ejemplo completo: services/inventory/app/adapters/api.py
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..domain.model import Profile, ProfileNotFound, VehicleType

SERVICE_NAME = "profiles"

router = APIRouter()


class ProfileIn(BaseModel):
    user_id: str
    name: str
    email: str


class ProfileUpdateIn(BaseModel):
    name: str
    phone_number: str | None = None
    preferred_vehicle_type: VehicleType | None = None


@router.get("/health")
def health(request: Request):
    try:
        request.app.state.profiles_service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


@router.post("/profiles", response_model=Profile, status_code=201)
def create_profile(body: ProfileIn, request: Request):
    try:
        return request.app.state.profiles_service.create_profile(body.user_id, body.name, body.email)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/profiles/{user_id}", response_model=Profile)
def get_profile(user_id: str, request: Request):
    try:
        return request.app.state.profiles_service.get_profile(user_id)
    except ProfileNotFound as exc:
        raise HTTPException(status_code=404, detail="Perfil no encontrado") from exc


@router.put("/profiles/{user_id}", response_model=Profile)
def update_profile(user_id: str, body: ProfileUpdateIn, request: Request):
    try:
        return request.app.state.profiles_service.update_profile(
            user_id, body.name, body.phone_number, body.preferred_vehicle_type
        )
    except ProfileNotFound as exc:
        raise HTTPException(status_code=404, detail="Perfil no encontrado") from exc


@router.delete("/profiles/{user_id}", response_model=Profile)
def deactivate_profile(user_id: str, request: Request):
    """Baja lógica: no borra la fila, pone active=False."""
    try:
        return request.app.state.profiles_service.deactivate_profile(user_id)
    except ProfileNotFound as exc:
        raise HTTPException(status_code=404, detail="Perfil no encontrado") from exc

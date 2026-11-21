"""Adaptador de entrada: endpoints REST de identity.

Solo traduce HTTP <-> dominio. La lógica va en domain/service.py.
Ejemplo completo: services/inventory/app/adapters/api.py
"""

from fastapi import APIRouter, HTTPException, Request

from ..domain.model import (
    InvalidCredentials,
    InvalidToken,
    UserAlreadyExists,
    UserNotFound,
    WeakPassword,
)

SERVICE_NAME = "identity"

router = APIRouter()


@router.get("/health")
def health(request: Request):
    service = request.app.state.identity_service
    try:
        service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


@router.get("/users/{user_id}")
def get_user(user_id: str, request: Request):
    identity_service = request.app.state.identity_service
    try:
        return identity_service.get_user(user_id)
    except UserNotFound as exc:
        raise HTTPException(status_code=404, detail="Usuario no encontrado") from exc


@router.post("/users")
def register_user(email: str, password: str, role: str, request: Request):
    identity_service = request.app.state.identity_service
    try:
        return identity_service.register_user(email, password, role)
    except WeakPassword as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UserAlreadyExists as exc:
        raise HTTPException(status_code=409, detail="El usuario ya existe") from exc


@router.post("/validate")
def validate_token(token: str, request: Request):
    identity_service = request.app.state.identity_service
    try:
        return identity_service.validate_token(token)
    except InvalidToken as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc


@router.post("/login")
def login(email: str, password: str, request: Request):
    identity_service = request.app.state.identity_service
    try:
        return identity_service.login(email, password)
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail="Credenciales inválidas") from exc

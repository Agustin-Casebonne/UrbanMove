"""Adaptador de entrada: endpoints REST de identity.

Solo traduce HTTP <-> dominio. La lógica va en service.py.
Ejemplo completo: services/inventory/app/api.py
"""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from .domain.model import (
    InvalidCredentials,
    InvalidToken,
    UserAlreadyExists,
    UserNotFound,
    UserRole,
    WeakPassword,
)

SERVICE_NAME = "identity"

router = APIRouter()


class UserPublic(BaseModel):
    """Lo que se enseña hacia fuera: el User sin password_hash."""

    user_id: str
    email: str
    role: UserRole
    created_at: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    role: UserRole


class LoginRequest(BaseModel):
    email: str
    password: str


@router.get("/health")
def health(request: Request):
    service = request.app.state.identity_service
    try:
        service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


@router.get("/users/{user_id}", response_model=UserPublic)
def get_user(user_id: str, request: Request):
    identity_service = request.app.state.identity_service
    try:
        return identity_service.get_user(user_id)
    except UserNotFound as exc:
        raise HTTPException(status_code=404, detail="Usuario no encontrado") from exc


@router.post("/users", response_model=UserPublic, status_code=201)
def register_user(body: RegisterRequest, request: Request):
    identity_service = request.app.state.identity_service
    try:
        return identity_service.register_user(body.email, body.password, body.role)
    except WeakPassword as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UserAlreadyExists as exc:
        raise HTTPException(status_code=409, detail="El usuario ya existe") from exc


@router.post("/validate")
def validate_token(request: Request, authorization: Annotated[str | None, Header()] = None):
    identity_service = request.app.state.identity_service
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Token inválido")
    try:
        return identity_service.validate_token(token)
    except InvalidToken as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc


@router.post("/login")
def login(body: LoginRequest, request: Request):
    identity_service = request.app.state.identity_service
    try:
        return identity_service.login(body.email, body.password)
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail="Credenciales inválidas") from exc

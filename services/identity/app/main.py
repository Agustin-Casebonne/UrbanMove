"""Microservicio Identity.

Responsabilidad: Autenticación, sesiones, tokens y roles (USER, MAINTENANCE, ADMIN).

TODO:
- POST /login -> token
- POST /register-credentials
- GET /validate (valida token y devuelve rol)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

from .adapters.api import SERVICE_NAME, router

logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aquí se inicializa la base de datos propia del servicio (ver services/inventory/app/main.py)
    yield


app = FastAPI(
    title="UrbanMove - Identity",
    version="0.1.0",
    description="Autenticación, sesiones, tokens y roles (USER, MAINTENANCE, ADMIN).",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)

app.include_router(router)

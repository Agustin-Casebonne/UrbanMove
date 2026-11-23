"""Microservicio Profiles.

Responsabilidad: Datos de usuario, preferencias, validación básica y baja lógica. No emite tokens.

TODO:
- POST /users -> publica UserRegistered
- GET /users/{id}
- PATCH /users/{id}
- DELETE /users/{id} (baja lógica)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

from .adapters.api import SERVICE_NAME, router

from .domain.service import ProfileService

from .adapters.db import init_db, SqliteProfileRepository

logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.profiles_service = ProfileService(SqliteProfileRepository())
    yield


app = FastAPI(
    title="UrbanMove - Profiles",
    version="0.1.0",
    description="Datos de usuario, preferencias, validación básica y baja lógica. No emite tokens.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)

app.include_router(router)

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

SERVICE_NAME = "profiles"
logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aquí se inicializa la base de datos propia del servicio (ver services/inventory/app/db.py)
    yield


app = FastAPI(
    title="UrbanMove - Profiles",
    version="0.1.0",
    description="Datos de usuario, preferencias, validación básica y baja lógica. No emite tokens.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}

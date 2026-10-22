"""Microservicio Rides.

Responsabilidad: Inicio y fin de viajes: duración, zona de origen/destino y coste preliminar.

TODO:
- POST /rides/start -> publica RideStarted
- POST /rides/{id}/finish -> publica RideFinished
- GET /rides?user_id=
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

SERVICE_NAME = "rides"
logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aquí se inicializa la base de datos propia del servicio (ver services/inventory/app/db.py)
    yield


app = FastAPI(
    title="UrbanMove - Rides",
    version="0.1.0",
    description="Inicio y fin de viajes: duración, zona de origen/destino y coste preliminar.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}

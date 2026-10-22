"""Microservicio History.

Responsabilidad: Histórico de reservas, viajes, incidencias y mantenimiento. Se alimenta de eventos (cola SQS propia).

TODO:
- Consumidor de la cola urbanmove-history (idempotente por event_id)
- GET /history/users/{id}
- GET /history/vehicles/{id}
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

SERVICE_NAME = "history"
logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aquí se inicializa la base de datos propia del servicio (ver services/inventory/app/db.py)
    yield


app = FastAPI(
    title="UrbanMove - History",
    version="0.1.0",
    description="Histórico de reservas, viajes, incidencias y mantenimiento. Se alimenta de eventos (cola SQS propia).",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}

"""Microservicio Analytics.

Responsabilidad: Consultas agregadas de demanda, flota, reservas y viajes a partir de los data marts. Alimenta el dashboard.

TODO:
- GET /kpis/fleet
- GET /kpis/demand?zone=&hour=
- GET /kpis/maintenance
- GET /kpis/health
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

SERVICE_NAME = "analytics"
logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aquí se inicializa la base de datos propia del servicio (ver services/inventory/app/db.py)
    yield


app = FastAPI(
    title="UrbanMove - Analytics",
    version="0.1.0",
    description="Consultas agregadas de demanda, flota, reservas y viajes a partir de los data marts. Alimenta el dashboard.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}

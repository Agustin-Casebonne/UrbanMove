"""Microservicio Maintenance.

Responsabilidad: Órdenes de mantenimiento: retirada, recarga, reparación, revisión y reincorporación.

TODO:
- POST /orders (también la crea la Lambda de detección)
- POST /orders/{id}/withdraw -> publica VehicleWithdrawnForMaintenance
- POST /orders/{id}/complete -> publica VehicleReturnedToService
- GET /orders?status=
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
    title="UrbanMove - Maintenance",
    version="0.1.0",
    description="Órdenes de mantenimiento: retirada, recarga, reparación, revisión y reincorporación.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)

app.include_router(router)

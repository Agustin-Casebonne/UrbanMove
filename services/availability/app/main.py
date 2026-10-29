"""Microservicio Availability.

Responsabilidad: Estado operativo de cada vehículo (AVAILABLE, RESERVED, IN_USE, LOW_BATTERY, WITHDRAWN, CHARGING, REPAIRING, READY_FOR_SERVICE, RETIRED) y su zona.

TODO:
- GET /availability?zone=Z01
- POST /vehicles/{id}/transition (valida la máquina de estados)
- Consume VehiclePurchased, VehicleReserved, ReservationCancelled/Expired, RideStarted/Finished, eventos de mantenimiento
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
    title="UrbanMove - Availability",
    version="0.1.0",
    description="Estado operativo de cada vehículo (AVAILABLE, RESERVED, IN_USE, LOW_BATTERY, WITHDRAWN, CHARGING, REPAIRING, READY_FOR_SERVICE, RETIRED) y su zona.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)

app.include_router(router)

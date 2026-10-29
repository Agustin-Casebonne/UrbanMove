"""Microservicio Reservations.

Responsabilidad: Crea, confirma, cancela y expira reservas. Evita reservar dos veces el mismo vehículo.

TODO:
- POST /reservations -> publica VehicleReserved
- POST /reservations/{id}/confirm
- POST /reservations/{id}/cancel -> publica ReservationCancelled
- POST /reservations/{id}/expire (lo llama la Lambda) -> publica ReservationExpired
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
    title="UrbanMove - Reservations",
    version="0.1.0",
    description="Crea, confirma, cancela y expira reservas. Evita reservar dos veces el mismo vehículo.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)

app.include_router(router)

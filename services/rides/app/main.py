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

from .adapters.api import SERVICE_NAME, router
from .adapters.db import init_db
from .domain.service import RideService
from .adapters.db import SqliteRideRepository
from .adapters.events import SnsEventPublisher
from .adapters.availability import HttpAvailabilityChecker

logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.ride_service = RideService(
        ride_repository=SqliteRideRepository(),
        availability_checker=HttpAvailabilityChecker(),
        event_publisher=SnsEventPublisher(),
    )
    yield


app = FastAPI(
    title="UrbanMove - Rides",
    version="0.1.0",
    description="Inicio y fin de viajes: duración, zona de origen/destino y coste preliminar.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)

app.include_router(router)

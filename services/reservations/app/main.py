"""Microservicio de RESERVAS.

Responsabilidad: crear, confirmar, cancelar y expirar reservas, y garantizar
que un vehículo no se reserva dos veces.

NO decide si un vehículo está disponible (eso es de availability) ni gestiona
viajes (eso es de rides). Se comunica con ellos por eventos y, al crear una
reserva, consultando a availability si AVAILABILITY_URL está configurada.

Estructura hexagonal:
- domain/model.py          -> Reservation, ReservationStatus, errores
- domain/service.py        -> lógica de negocio (solo usa los puertos)
- ports/ports.py           -> contratos: ReservationRepository, EventPublisher, AvailabilityChecker
- adapters/api.py          -> entrada: endpoints REST
- adapters/db.py           -> salida: SQLite (implementa ReservationRepository)
- adapters/events.py       -> salida: SNS (implementa EventPublisher)
- adapters/availability.py -> salida: HTTP a availability (implementa AvailabilityChecker)

Configuración (variables de entorno):
- DB_PATH                     ruta de la base de datos SQLite
- RESERVATION_TTL_MINUTES     minutos para confirmar una reserva (por defecto 5)
- CONFIRMED_HOLD_MINUTES      minutos que se guarda el vehículo tras confirmar (por defecto 15)
- AVAILABILITY_URL            URL del servicio availability (opcional)
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

from .adapters.api import SERVICE_NAME, register_error_handlers, router
from .adapters.availability import HttpAvailabilityChecker
from .adapters.db import SqliteReservationRepository, init_db
from .adapters.events import SnsEventPublisher
from .domain.service import ReservationService

logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    availability_url = os.getenv("AVAILABILITY_URL")
    if not availability_url:
        logger.warning("AVAILABILITY_URL no configurada: no se comprobará la disponibilidad al reservar")
    app.state.reservation_service = ReservationService(
        repository=SqliteReservationRepository(),
        publisher=SnsEventPublisher(SERVICE_NAME),
        availability=HttpAvailabilityChecker(availability_url) if availability_url else None,
        pending_ttl_minutes=float(os.getenv("RESERVATION_TTL_MINUTES", "5")),
        confirmed_hold_minutes=float(os.getenv("CONFIRMED_HOLD_MINUTES", "15")),
    )
    yield


app = FastAPI(
    title="UrbanMove - Reservations",
    version="1.0.0",
    description="Crea, confirma, cancela y expira reservas. Evita reservar dos veces el mismo vehículo.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)
register_error_handlers(app)
app.include_router(router)

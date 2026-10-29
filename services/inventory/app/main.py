"""Microservicio de INVENTARIO de recursos.

Responsabilidad: registrar bicicletas y patinetes como activos (identificador,
tipo, modelo, fecha de compra) y su estado ADMINISTRATIVO (ACTIVE / RETIRED).

NO gestiona si un vehículo está disponible, reservado o en uso: eso es del
servicio de disponibilidad.

Estructura hexagonal:
- domain/model.py    -> VehicleType, AdminStatus, Vehicle
- domain/service.py  -> lógica de negocio (solo usa los puertos)
- ports/ports.py     -> contratos: VehicleRepository, EventPublisher
- adapters/api.py    -> entrada: endpoints REST
- adapters/db.py     -> salida: SQLite (implementa VehicleRepository)
- adapters/events.py -> salida: SNS (implementa EventPublisher)

Este fichero conecta cada adaptador con el dominio.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

from .adapters.api import SERVICE_NAME, router
from .adapters.db import SqliteVehicleRepository, init_db
from .adapters.events import SnsEventPublisher
from .domain.service import InventoryService

logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.inventory_service = InventoryService(
        repository=SqliteVehicleRepository(),
        publisher=SnsEventPublisher(SERVICE_NAME),
    )
    yield


app = FastAPI(
    title="UrbanMove - Inventario",
    version="1.0.0",
    description="Registro de bicicletas y patinetes como activos.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)
app.include_router(router)

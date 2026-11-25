"""Microservicio Maintenance.

Responsabilidad: órdenes de mantenimiento: retirada, recarga, reparación,
revisión y reincorporación.

- POST /orders                    (también la llama la Lambda maintenance_detector)
- GET  /orders?status=&vehicle_id=
- GET  /orders/{id}
- POST /orders/{id}/assign
- POST /orders/{id}/withdraw      -> publica VehicleWithdrawnForMaintenance
- POST /orders/{id}/complete      -> publica VehicleReturnedToService
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

from .adapters.db import SqliteMaintenanceOrderRepository, init_db
from .adapters.events import SnsEventPublisher
from .api import SERVICE_NAME, router
from .service import MaintenanceService

logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.maintenance_service = MaintenanceService(
        repository=SqliteMaintenanceOrderRepository(),
        publisher=SnsEventPublisher(SERVICE_NAME),
    )
    yield


app = FastAPI(
    title="UrbanMove - Maintenance",
    version="1.0.0",
    description="Órdenes de mantenimiento: retirada, recarga, reparación, revisión y reincorporación.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)
app.include_router(router)
"""Microservicio Relocation.

Responsabilidad: órdenes de recolocación entre zonas a partir de indicadores de
demanda.

- POST /orders                    -> publica RelocationOrderCreated
- GET  /orders?status=&to_zone=
- GET  /orders/{id}
- POST /orders/{id}/assign
- POST /orders/{id}/start
- POST /orders/{id}/complete      -> publica RelocationOrderCompleted
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

from .adapters.db import SqliteRelocationOrderRepository, init_db
from .adapters.events import SnsEventPublisher
from .api import SERVICE_NAME, router
from .service import RelocationService

logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.relocation_service = RelocationService(
        repository=SqliteRelocationOrderRepository(),
        publisher=SnsEventPublisher(SERVICE_NAME),
    )
    yield


app = FastAPI(
    title="UrbanMove - Relocation",
    version="1.0.0",
    description="Órdenes de recolocación entre zonas a partir de indicadores de demanda.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)
app.include_router(router)

"""Microservicio History.

Responsabilidad: histórico de reservas, viajes, incidencias y mantenimiento.
Se alimenta de eventos desde su propia cola SQS (urbanmove-history).

- Consumidor de la cola urbanmove-history (idempotente por event_id)
- GET /history/users/{id}
- GET /history/vehicles/{id}
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.consumer import SqsEventConsumer
from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

from .adapters.api import SERVICE_NAME, router
from .adapters.db import SqliteHistoryRepository, init_db
from .domain.service import HistoryService

logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    service = HistoryService(SqliteHistoryRepository())
    app.state.history_service = service

    consumer = None
    if os.getenv("AWS_ENDPOINT_URL"):
        consumer = SqsEventConsumer("urbanmove-history", service.record_event)
        consumer.start()
    yield
    if consumer:
        consumer.stop()


app = FastAPI(
    title="UrbanMove - History",
    version="1.0.0",
    description="Histórico de reservas, viajes, incidencias y mantenimiento. Se alimenta de eventos.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)
app.include_router(router)

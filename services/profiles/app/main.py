"""Microservicio Profiles.

Responsabilidad: Datos de usuario, preferencias, validación básica y baja lógica. No emite tokens.

TODO:
- POST /users -> publica UserRegistered
- GET /users/{id}
- PATCH /users/{id}
- DELETE /users/{id} (baja lógica)
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.consumer import SqsEventConsumer
from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

from .adapters.api import SERVICE_NAME, router
from .adapters.db import SqliteProfileRepository, init_db
from .domain.service import ProfileService

logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    service = ProfileService(SqliteProfileRepository())
    app.state.profiles_service = service

    consumer = None
    if os.getenv("AWS_ENDPOINT_URL"):
        consumer = SqsEventConsumer(
            "urbanmove-profiles",
            lambda event: service.handle_event(event["event_type"], event["data"]),
        )
        consumer.start()
    yield
    if consumer:
        consumer.stop()


app = FastAPI(
    title="UrbanMove - Profiles",
    version="0.1.0",
    description="Datos de usuario, preferencias, validación básica y baja lógica. No emite tokens.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)

app.include_router(router)

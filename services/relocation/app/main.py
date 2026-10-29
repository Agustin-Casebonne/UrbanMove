"""Microservicio Relocation.

Responsabilidad: Órdenes de recolocación entre zonas a partir de indicadores de demanda.

TODO:
- POST /orders -> publica RelocationOrderCreated
- PATCH /orders/{id} (ASSIGNED, IN_PROGRESS)
- POST /orders/{id}/complete -> publica RelocationOrderCompleted
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
    title="UrbanMove - Relocation",
    version="0.1.0",
    description="Órdenes de recolocación entre zonas a partir de indicadores de demanda.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)

app.include_router(router)

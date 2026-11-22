import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

from .adapters.api import SERVICE_NAME, router
from .adapters.db import SqliteUserRepository, init_db
from .adapters.events import SnsEventPublisher
from .adapters.security import BcryptPasswordHasher, JwtTokenIssuer
from .domain.service import IdentityService

logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.identity_service = IdentityService(
        user_repository=SqliteUserRepository(),
        token_issuer=JwtTokenIssuer(
            secret_key=os.environ["JWT_SECRET"],
            expires_minutes=int(os.getenv("JWT_EXPIRES_MINUTES", "60")),
        ),
        password_hasher=BcryptPasswordHasher(),
        event_publisher=SnsEventPublisher(source=SERVICE_NAME),
    )
    yield


app = FastAPI(
    title="UrbanMove - Identity",
    version="0.1.0",
    description="Autenticación, sesiones, tokens y roles (USER, MAINTENANCE, ADMIN).",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)

app.include_router(router)

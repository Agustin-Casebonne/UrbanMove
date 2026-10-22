"""Logs estructurados (JSON) con identificador de correlación.

Cada petición HTTP lleva la cabecera X-Correlation-ID. Si no viene, se genera
una nueva. Ese ID se guarda en una variable de contexto, se escribe en todos
los logs y se copia en los eventos que se publiquen, para poder seguir un
flujo completo (app -> servicio -> evento -> Lambda -> Data Lake).
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

CORRELATION_HEADER = "X-Correlation-ID"

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(value: str | None) -> str:
    value = value or str(uuid.uuid4())
    _correlation_id.set(value)
    return value


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service,
            "correlation_id": get_correlation_id(),
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            entry.update(extra)
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def get_logger(service: str) -> logging.Logger:
    logger = logging.getLogger(service)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter(service))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def add_correlation_middleware(app, logger: logging.Logger) -> None:
    """Middleware de FastAPI: lee/genera el correlation id y loguea cada petición."""

    @app.middleware("http")
    async def correlation_middleware(request, call_next):
        cid = set_correlation_id(request.headers.get(CORRELATION_HEADER))
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = cid
        if request.url.path != "/health":
            logger.info(
                "request",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                    }
                },
            )
        return response

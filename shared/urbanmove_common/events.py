"""Formato estándar de los eventos de dominio y publicación en el bus.

Todos los eventos tienen la misma "envoltura" (ver docs/eventos.md):

{
  "event_id": "uuid",                 # identificador único (sirve para idempotencia)
  "event_type": "RideStarted",        # tipo de evento
  "schema_version": 1,                # versión del esquema de "data"
  "source": "rides",                  # microservicio que lo produce
  "timestamp": "2026-10-15T12:00:00+00:00",
  "correlation_id": "uuid",           # permite seguir un flujo completo
  "data": { ... }                     # contenido propio de cada evento
}

Los eventos se publican en un tópico SNS (urbanmove-events). De ahí salen
hacia colas SQS de cada consumidor (historial, Data Lake, Lambdas...).

Tolerancia a fallos:
- Reintentos controlados (3 intentos con espera creciente).
- Si el bus no está disponible, el evento se guarda en un fichero local
  (outbox) para reenviarlo después y NO se rompe la operación principal.
"""

import json
import os
import time
import uuid
from datetime import datetime, timezone

from .logging_utils import get_correlation_id, get_logger

EVENT_TYPES = {
    "UserRegistered",
    "VehiclePurchased",
    "VehicleReserved",
    "ReservationCancelled",
    "ReservationExpired",
    "RideStarted",
    "RideFinished",
    "VehicleBatteryLow",
    "VehicleWithdrawnForMaintenance",
    "VehicleReturnedToService",
    "DemandHotspotDetected",
    "RelocationOrderCreated",
    "RelocationOrderCompleted",
}

logger = get_logger("events")


def build_event(event_type: str, source: str, data: dict, schema_version: int = 1) -> dict:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Tipo de evento desconocido: {event_type}")
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "schema_version": schema_version,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": get_correlation_id(),
        "data": data,
    }


def _sns_client():
    import boto3

    return boto3.client(
        "sns",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


def _save_to_outbox(event: dict) -> None:
    path = os.getenv("OUTBOX_PATH", "outbox.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def publish_event(event: dict, retries: int = 3) -> bool:
    """Publica un evento en SNS. Devuelve True si se publicó.

    Si no hay tópico configurado (por ejemplo en los tests), solo se loguea.
    """
    topic_arn = os.getenv("EVENTS_TOPIC_ARN")
    log_fields = {"event_id": event["event_id"], "event_type": event["event_type"]}

    if not topic_arn:
        logger.info("event (bus no configurado)", extra={"extra_fields": log_fields})
        return False

    for attempt in range(1, retries + 1):
        try:
            _sns_client().publish(
                TopicArn=topic_arn,
                Message=json.dumps(event),
                MessageAttributes={
                    "event_type": {"DataType": "String", "StringValue": event["event_type"]},
                },
            )
            logger.info("event published", extra={"extra_fields": log_fields})
            return True
        except Exception as exc:  # noqa: BLE001 - queremos capturar cualquier fallo del bus
            logger.warning(
                f"error publicando evento (intento {attempt}/{retries}): {exc}",
                extra={"extra_fields": log_fields},
            )
            time.sleep(0.5 * attempt)

    _save_to_outbox(event)
    logger.error("evento guardado en outbox para reenvío", extra={"extra_fields": log_fields})
    return False


def emit(event_type: str, source: str, data: dict) -> dict:
    """Atajo: construye y publica un evento. Devuelve el evento."""
    event = build_event(event_type, source, data)
    publish_event(event)
    return event

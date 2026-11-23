"""Consumidor genérico de eventos desde una cola SQS (reutilizable por todos los servicios).

Uso (ver docs/eventos.md):

    consumer = SqsEventConsumer("urbanmove-profiles", handler)
    consumer.start()      # hilo en segundo plano
    ...
    consumer.stop()

`handler` recibe el evento completo (la "envoltura" de events.py) como dict.
- Si el handler termina bien, el mensaje se borra de la cola.
- Si lanza una excepción, NO se borra: SQS lo reintenta y, tras 3 fallos,
  lo mueve a la DLQ (RedrivePolicy definida en infra/localstack/init-aws.sh).
- Los mensajes con JSON inválido se borran (reintentar no los arreglaría).
"""

import json
import os
import threading
from typing import Callable

from .logging_utils import get_logger

logger = get_logger("consumer")


def _sqs_client():
    import boto3

    return boto3.client(
        "sqs",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


class SqsEventConsumer:
    def __init__(self, queue_name: str, handler: Callable[[dict], object], wait_seconds: int = 5):
        self.queue_name = queue_name
        self.handler = handler
        self.wait_seconds = wait_seconds
        self._stop = threading.Event()
        self._thread = None
        self._sqs = None
        self._queue_url = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=f"consumer-{self.queue_name}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.wait_seconds + 5)

    def _connect(self) -> bool:
        try:
            self._sqs = _sqs_client()
            self._queue_url = self._sqs.get_queue_url(QueueName=self.queue_name)["QueueUrl"]
            logger.info(f"escuchando cola {self.queue_name}")
            return True
        except Exception as exc:  # noqa: BLE001 - la cola puede no existir aún
            logger.warning(f"cola {self.queue_name} no disponible: {exc}")
            return False

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._queue_url is None and not self._connect():
                self._stop.wait(2)
                continue
            try:
                self.poll_once()
            except Exception as exc:  # noqa: BLE001 - el bucle nunca debe morir
                logger.error(f"error leyendo cola {self.queue_name}: {exc}")
                self._stop.wait(2)

    def poll_once(self) -> int:
        """Lee un lote de mensajes y los procesa. Devuelve cuántos se borraron."""
        response = self._sqs.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=self.wait_seconds,
        )
        deleted = 0
        for message in response.get("Messages", []):
            if self._process(message):
                self._sqs.delete_message(QueueUrl=self._queue_url, ReceiptHandle=message["ReceiptHandle"])
                deleted += 1
        return deleted

    def _process(self, message: dict) -> bool:
        try:
            event = json.loads(message["Body"])
        except (ValueError, TypeError):
            logger.error("mensaje con JSON inválido, se descarta")
            return True
        try:
            self.handler(event)
            return True
        except Exception as exc:  # noqa: BLE001 - se deja en la cola para reintento/DLQ
            logger.error(f"error procesando {event.get('event_type')} ({event.get('event_id')}): {exc}")
            return False

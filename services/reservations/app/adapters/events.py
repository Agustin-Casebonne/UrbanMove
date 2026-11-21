"""Adaptador de salida: publica eventos en SNS. Implementa ports.EventPublisher.

Eventos de reservations: VehicleReserved, ReservationCancelled, ReservationExpired.
La librería común se encarga de reintentos y del outbox si el bus está caído.
"""

from urbanmove_common.events import emit

from ..ports.ports import EventPublisher


class SnsEventPublisher(EventPublisher):
    def __init__(self, source: str):
        self.source = source

    def publish(self, event_type: str, data: dict) -> None:
        emit(event_type, self.source, data)

"""Adaptador de salida: publica eventos en SNS.

Eventos de rides: RideStarted, RideFinished.
Ejemplo: services/inventory/app/adapters/events.py
"""

from urbanmove_common.events import emit

from ..ports.ports import EventPublisher


class SnsEventPublisher(EventPublisher):
    def __init__(self, source: str):
        self.source = source

    def publish(self, event_type: str, data: dict) -> None:
        emit(event_type, self.source, data)

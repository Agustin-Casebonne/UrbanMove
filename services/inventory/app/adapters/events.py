"""Adaptador de salida: publica eventos en SNS. Implementa ports.EventPublisher."""

from urbanmove_common.events import emit


class SnsEventPublisher:
    def __init__(self, source: str):
        self.source = source

    def publish(self, event_type: str, data: dict) -> None:
        emit(event_type, self.source, data)

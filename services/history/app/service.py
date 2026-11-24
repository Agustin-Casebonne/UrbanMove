"""Lógica de negocio de history. Solo usa domain/model.py y ports/ports.py.

Ejemplo: services/inventory/app/service.py
"""

from .domain.model import HistoryEntry
from .ports.ports import HistoryRepository


class HistoryService:
    def __init__(self, repository: HistoryRepository):
        self.repository = repository

    def check_health(self):
        self.repository.ping()

    def record_event(self, event):
        """Guarda un evento en el historial.

        Devuelve True si era nuevo y False si ya estaba (evento duplicado).
        Si el evento está mal formado lanza KeyError: el consumidor no borra
        el mensaje, SQS lo reintenta y acaba en la DLQ.
        """
        if self.repository.exists(event["event_id"]):
            return False

        data = event.get("data", {})
        entry = HistoryEntry(
            event_id=event["event_id"],
            event_type=event["event_type"],
            user_id=data.get("user_id"),
            vehicle_id=data.get("vehicle_id"),
            timestamp=event["timestamp"],
            correlation_id=event["correlation_id"],
            payload=data,
        )
        self.repository.save(entry)
        return True

    def get_user_history(self, user_id):
        return self.repository.by_user(user_id)

    def get_vehicle_history(self, vehicle_id):
        return self.repository.by_vehicle(vehicle_id)

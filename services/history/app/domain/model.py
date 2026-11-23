from pydantic import BaseModel


class HistoryEntry(BaseModel):
    event_id: str
    event_type: str
    user_id: str | None = None
    vehicle_id: str | None = None
    timestamp: str
    correlation_id: str
    payload: dict

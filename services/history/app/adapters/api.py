"""Adaptador de entrada: endpoints REST de history.

Solo traduce HTTP <-> dominio (JSON, códigos 200/503). La lógica está
en domain/service.py. History es de solo lectura por HTTP: los datos
entran por la cola SQS (ver main.py).
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from ..domain.model import HistoryEntry
from ..domain.service import HistoryService

SERVICE_NAME = "history"

router = APIRouter()


def get_service(request: Request) -> HistoryService:
    """El servicio lo crea main.py al arrancar."""
    return request.app.state.history_service


@router.get("/health")
def health(service: HistoryService = Depends(get_service)):
    try:
        service.check_health()
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


@router.get("/history/users/{user_id}", response_model=list[HistoryEntry])
def get_user_history(user_id: str, service: HistoryService = Depends(get_service)):
    return service.get_user_history(user_id)


@router.get("/history/vehicles/{vehicle_id}", response_model=list[HistoryEntry])
def get_vehicle_history(vehicle_id: str, service: HistoryService = Depends(get_service)):
    return service.get_vehicle_history(vehicle_id)

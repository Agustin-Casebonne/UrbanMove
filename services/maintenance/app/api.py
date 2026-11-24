"""Adaptador de entrada: endpoints REST de maintenance.

Solo traduce HTTP <-> dominio. La lógica va en service.py.
Ejemplo completo: services/inventory/app/api.py
"""

from fastapi import APIRouter

SERVICE_NAME = "maintenance"

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}

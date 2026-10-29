"""Adaptador de entrada: endpoints REST de analytics.

Solo traduce HTTP <-> dominio. La lógica va en domain/service.py.
Ejemplo completo: services/inventory/app/adapters/api.py
"""

from fastapi import APIRouter

SERVICE_NAME = "analytics"

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}

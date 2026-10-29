"""Adaptador de entrada: endpoints REST de relocation.

Solo traduce HTTP <-> dominio. La lógica va en domain/service.py.
Ejemplo completo: services/inventory/app/adapters/api.py
"""

from fastapi import APIRouter

SERVICE_NAME = "relocation"

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}

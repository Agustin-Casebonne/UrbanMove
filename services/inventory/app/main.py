"""Microservicio de INVENTARIO de recursos.

Responsabilidad: registrar bicicletas y patinetes como activos (identificador,
tipo, modelo, fecha de compra) y su estado ADMINISTRATIVO (ACTIVE / RETIRED).

NO gestiona si un vehículo está disponible, reservado o en uso: eso es del
servicio de disponibilidad.

Eventos que publica:
- VehiclePurchased: al dar de alta un vehículo nuevo.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from urbanmove_common.events import emit
from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

from .db import get_conn, init_db

SERVICE_NAME = "inventory"
logger = get_logger(SERVICE_NAME)


class VehicleType(str, Enum):
    BIKE = "BIKE"
    SCOOTER = "SCOOTER"


class AdminStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class VehicleIn(BaseModel):
    vehicle_type: VehicleType
    model: str = Field(min_length=1, examples=["Xiaomi Pro 2"])
    purchase_date: date
    initial_zone: str = Field(min_length=1, examples=["Z01"])


class Vehicle(VehicleIn):
    vehicle_id: str
    admin_status: AdminStatus
    created_at: str


class AdminStatusIn(BaseModel):
    admin_status: AdminStatus


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="UrbanMove - Inventario",
    version="1.0.0",
    description="Registro de bicicletas y patinetes como activos.",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)


def _row_to_vehicle(row) -> Vehicle:
    return Vehicle(**dict(row))


@app.get("/health")
def health():
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "service": SERVICE_NAME}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db error: {exc}") from exc


@app.post("/vehicles", response_model=Vehicle, status_code=201)
def create_vehicle(body: VehicleIn):
    vehicle_id = f"{body.vehicle_type.value[0]}-{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO vehicles VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                vehicle_id,
                body.vehicle_type.value,
                body.model,
                body.purchase_date.isoformat(),
                body.initial_zone,
                AdminStatus.ACTIVE.value,
                created_at,
            ),
        )
    vehicle = Vehicle(
        **body.model_dump(),
        vehicle_id=vehicle_id,
        admin_status=AdminStatus.ACTIVE,
        created_at=created_at,
    )
    logger.info("vehicle created", extra={"extra_fields": {"vehicle_id": vehicle_id}})
    emit("VehiclePurchased", SERVICE_NAME, vehicle.model_dump(mode="json"))
    return vehicle


@app.get("/vehicles", response_model=list[Vehicle])
def list_vehicles(vehicle_type: VehicleType | None = None, admin_status: AdminStatus | None = None):
    query = "SELECT * FROM vehicles WHERE 1=1"
    params: list = []
    if vehicle_type:
        query += " AND vehicle_type = ?"
        params.append(vehicle_type.value)
    if admin_status:
        query += " AND admin_status = ?"
        params.append(admin_status.value)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_vehicle(r) for r in rows]


@app.get("/vehicles/{vehicle_id}", response_model=Vehicle)
def get_vehicle(vehicle_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return _row_to_vehicle(row)


@app.patch("/vehicles/{vehicle_id}/admin-status", response_model=Vehicle)
def update_admin_status(vehicle_id: str, body: AdminStatusIn):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE vehicles SET admin_status = ? WHERE vehicle_id = ?",
            (body.admin_status.value, vehicle_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return get_vehicle(vehicle_id)

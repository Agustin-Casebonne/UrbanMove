"""Adaptador de salida: base de datos propia del servicio de inventario (SQLite).

Implementa ports.VehicleRepository. Es el único sitio donde hay SQL.

Ningún otro microservicio accede a esta base de datos: si necesitan datos de
un vehículo, llaman a la API de inventario o escuchan sus eventos.
"""

import os
import sqlite3

from ..domain.model import AdminStatus, Vehicle


def db_path() -> str:
    return os.getenv("DB_PATH", "inventory.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id     TEXT PRIMARY KEY,
                vehicle_type   TEXT NOT NULL,      -- BIKE | SCOOTER
                model          TEXT NOT NULL,
                purchase_date  TEXT NOT NULL,
                initial_zone   TEXT NOT NULL,
                admin_status   TEXT NOT NULL,      -- ACTIVE | RETIRED
                created_at     TEXT NOT NULL
            )
            """
        )


def _row_to_vehicle(row) -> Vehicle:
    return Vehicle(**dict(row))


class SqliteVehicleRepository:
    def ping(self) -> None:
        with get_conn() as conn:
            conn.execute("SELECT 1")

    def save(self, vehicle: Vehicle) -> None:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO vehicles VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    vehicle.vehicle_id,
                    vehicle.vehicle_type.value,
                    vehicle.model,
                    vehicle.purchase_date.isoformat(),
                    vehicle.initial_zone,
                    vehicle.admin_status.value,
                    vehicle.created_at,
                ),
            )

    def get(self, vehicle_id: str) -> Vehicle | None:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,)).fetchone()
        return _row_to_vehicle(row) if row else None

    def list_all(self) -> list[Vehicle]:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM vehicles").fetchall()
        return [_row_to_vehicle(r) for r in rows]

    def update_admin_status(self, vehicle_id: str, admin_status: AdminStatus) -> bool:
        with get_conn() as conn:
            cur = conn.execute(
                "UPDATE vehicles SET admin_status = ? WHERE vehicle_id = ?",
                (admin_status.value, vehicle_id),
            )
        return cur.rowcount > 0

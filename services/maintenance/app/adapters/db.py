"""Adaptador de salida: base de datos propia de maintenance (SQLite).

Implementa ports.MaintenanceOrderRepository. Es el único sitio donde hay SQL.
Ningún otro microservicio accede a esta base de datos.

CÓMO SE EVITAN ÓRDENES DUPLICADAS (idempotencia)
Un índice único PARCIAL: solo cuentan las órdenes que no están COMPLETED.
- Un vehículo puede tener muchas órdenes antiguas completadas, pero como
  mucho UNA abierta.
- Si llega dos veces el mismo VehicleBatteryLow, el segundo INSERT falla con
  IntegrityError y se traduce a OrderAlreadyOpen.

Los cambios de estado usan UPDATE ... WHERE status = ?: si dos peticiones
llegan a la vez, solo una cambia la fila.
"""

import os
import sqlite3

from ..domain.model import MaintenanceOrder, MaintenanceStatus, OrderAlreadyOpen
from ..ports.ports import MaintenanceOrderRepository


def db_path() -> str:
    return os.getenv("DB_PATH", "maintenance.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS maintenance_orders (
                order_id    TEXT PRIMARY KEY,
                vehicle_id  TEXT NOT NULL,
                type        TEXT NOT NULL,      -- CHARGE | REPAIR | REVIEW
                status      TEXT NOT NULL,      -- OPEN | ASSIGNED | IN_PROGRESS | COMPLETED
                reason      TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS one_open_order_per_vehicle
            ON maintenance_orders (vehicle_id) WHERE status != 'COMPLETED'
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON maintenance_orders (status)")


def _row_to_order(row) -> MaintenanceOrder:
    return MaintenanceOrder(**dict(row))


class SqliteMaintenanceOrderRepository(MaintenanceOrderRepository):
    def ping(self) -> None:
        with get_conn() as conn:
            conn.execute("SELECT 1")

    def save(self, order: MaintenanceOrder) -> None:
        try:
            with get_conn() as conn:
                conn.execute(
                    "INSERT INTO maintenance_orders VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        order.order_id,
                        order.vehicle_id,
                        order.type.value,
                        order.status.value,
                        order.reason,
                        order.created_at,
                        order.updated_at,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise OrderAlreadyOpen(order.vehicle_id) from exc

    def get(self, order_id: str) -> MaintenanceOrder | None:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM maintenance_orders WHERE order_id = ?", (order_id,)).fetchone()
        return _row_to_order(row) if row else None

    def list_orders(
        self, status: MaintenanceStatus | None = None, vehicle_id: str | None = None
    ) -> list[MaintenanceOrder]:
        query = "SELECT * FROM maintenance_orders WHERE 1 = 1"
        params: list[str] = []
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        if vehicle_id is not None:
            query += " AND vehicle_id = ?"
            params.append(vehicle_id)
        query += " ORDER BY created_at DESC"
        with get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_order(r) for r in rows]

    def transition(
        self,
        order_id: str,
        from_status: MaintenanceStatus,
        to_status: MaintenanceStatus,
        updated_at: str,
    ) -> bool:
        with get_conn() as conn:
            cur = conn.execute(
                """
                UPDATE maintenance_orders
                SET status = ?, updated_at = ?
                WHERE order_id = ? AND status = ?
                """,
                (to_status.value, updated_at, order_id, from_status.value),
            )
        return cur.rowcount > 0
"""Adaptador de salida: base de datos propia de relocation (SQLite).

Implementa ports.RelocationOrderRepository. Es el único sitio donde hay SQL.
Ningún otro microservicio accede a esta base de datos.

CÓMO SE EVITAN ÓRDENES DUPLICADAS (idempotencia)
Un índice único PARCIAL: solo cuentan las órdenes que no están COMPLETED.
- Un trayecto y tipo de vehículo puede tener muchas órdenes antiguas
  completadas, pero como mucho UNA abierta.
- Si la Lambda de recolocación detecta dos veces el mismo déficit, el segundo
  INSERT falla con IntegrityError y se traduce a OrderAlreadyOpen.

Los cambios de estado usan UPDATE ... WHERE status = ?: si dos peticiones
llegan a la vez, solo una cambia la fila.

vehicle_ids es una lista: se guarda como texto JSON.
"""

import json
import os
import sqlite3

from ..domain.model import OrderAlreadyOpen, RelocationOrder, RelocationStatus
from ..ports.ports import RelocationOrderRepository


def db_path() -> str:
    return os.getenv("DB_PATH", "relocation.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relocation_orders (
                order_id      TEXT PRIMARY KEY,
                from_zone     TEXT NOT NULL,
                to_zone       TEXT NOT NULL,
                vehicle_type  TEXT NOT NULL,
                quantity      INTEGER NOT NULL,
                reason        TEXT NOT NULL,
                status        TEXT NOT NULL,
                vehicle_ids   TEXT NOT NULL,
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL,
                completed_at  TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS one_open_order_per_route
            ON relocation_orders (from_zone, to_zone, vehicle_type) WHERE status != 'COMPLETED'
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON relocation_orders (status)")


def _row_to_order(row) -> RelocationOrder:
    data = dict(row)
    data["vehicle_ids"] = json.loads(data["vehicle_ids"])
    return RelocationOrder(**data)


class SqliteRelocationOrderRepository(RelocationOrderRepository):
    def ping(self) -> None:
        with get_conn() as conn:
            conn.execute("SELECT 1")

    def save(self, order: RelocationOrder) -> None:
        try:
            with get_conn() as conn:
                conn.execute(
                    "INSERT INTO relocation_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        order.order_id,
                        order.from_zone,
                        order.to_zone,
                        order.vehicle_type.value,
                        order.quantity,
                        order.reason,
                        order.status.value,
                        json.dumps(order.vehicle_ids),
                        order.created_at,
                        order.updated_at,
                        order.completed_at,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            route = f"{order.from_zone} → {order.to_zone} ({order.vehicle_type.value})"
            raise OrderAlreadyOpen(route) from exc

    def get(self, order_id: str) -> RelocationOrder | None:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM relocation_orders WHERE order_id = ?", (order_id,)).fetchone()
        return _row_to_order(row) if row else None

    def list_orders(
        self, status: RelocationStatus | None = None, to_zone: str | None = None
    ) -> list[RelocationOrder]:
        query = "SELECT * FROM relocation_orders WHERE 1 = 1"
        params: list[str] = []
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        if to_zone is not None:
            query += " AND to_zone = ?"
            params.append(to_zone)
        query += " ORDER BY created_at DESC"
        with get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_order(r) for r in rows]

    def transition(
        self,
        order_id: str,
        from_status: RelocationStatus,
        to_status: RelocationStatus,
        updated_at: str,
    ) -> bool:
        with get_conn() as conn:
            cur = conn.execute(
                """
                UPDATE relocation_orders
                SET status = ?, updated_at = ?
                WHERE order_id = ? AND status = ?
                """,
                (to_status.value, updated_at, order_id, from_status.value),
            )
        return cur.rowcount > 0

    def complete(self, order_id: str, vehicle_ids: list[str], completed_at: str) -> bool:
        with get_conn() as conn:
            cur = conn.execute(
                """
                UPDATE relocation_orders
                SET status = 'COMPLETED', vehicle_ids = ?, completed_at = ?, updated_at = ?
                WHERE order_id = ? AND status = 'IN_PROGRESS'
                """,
                (json.dumps(vehicle_ids), completed_at, completed_at, order_id),
            )
        return cur.rowcount > 0

"""Adaptador de salida: base de datos propia de history (SQLite).

Ningún otro microservicio accede a esta base de datos.
Ejemplo: services/inventory/app/adapters/db.py
"""

import json
import os
import sqlite3

from ..domain.model import HistoryEntry
from ..ports.ports import HistoryRepository


def db_path() -> str:
    return os.getenv("DB_PATH", "history.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=5)
    conn.row_factory = sqlite3.Row  
    return conn

def init_db() -> None:
    """Crea la tabla si no existe. Se llama al arrancar el servicio."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                user_id                 TEXT,
                event_id                TEXT PRIMARY KEY,
                event_type              TEXT NOT NULL,
                vehicle_id              TEXT,
                timestamp               TEXT NOT NULL,              
                correlation_id          TEXT NOT NULL,
                payload                 TEXT NOT NULL
            )
            """
        )


class SqliteHistoryRepository(HistoryRepository):
    def ping(self) -> None:
        with get_conn() as conn:
            conn.execute("SELECT 1")


    def save(self, entry):
        with get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO history "
                "(user_id, event_id, event_type, vehicle_id, timestamp, correlation_id, payload) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    entry.user_id,
                    entry.event_id,
                    entry.event_type,
                    entry.vehicle_id,
                    entry.timestamp,
                    entry.correlation_id,
                    json.dumps(entry.payload),
                ),
            )

    def exists(self, event_id):
        with get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM history WHERE event_id = ?", (event_id,)
            ).fetchone()
        return row is not None

    def by_user(self, user_id):
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM history WHERE user_id = ? ORDER BY timestamp",
                (user_id,),
            ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def by_vehicle(self, vehicle_id):
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM history WHERE vehicle_id = ? ORDER BY timestamp",
                (vehicle_id,),
            ).fetchall()
        return [_row_to_entry(r) for r in rows]


def _row_to_entry(row):
    return HistoryEntry(
        event_id=row["event_id"],
        event_type=row["event_type"],
        user_id=row["user_id"],
        vehicle_id=row["vehicle_id"],
        timestamp=row["timestamp"],
        correlation_id=row["correlation_id"],
        payload=json.loads(row["payload"]),
    )

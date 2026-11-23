"""Adaptador de salida: base de datos propia de history (SQLite).

Ningún otro microservicio accede a esta base de datos.
Ejemplo: services/inventory/app/adapters/db.py
"""

import os
import sqlite3

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

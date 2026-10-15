"""Base de datos propia del servicio de inventario (SQLite).

Ningún otro microservicio accede a esta base de datos: si necesitan datos de
un vehículo, llaman a la API de inventario o escuchan sus eventos.
"""

import os
import sqlite3


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

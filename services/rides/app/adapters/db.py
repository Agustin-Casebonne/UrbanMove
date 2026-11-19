"""Adaptador de salida: base de datos propia de rides (SQLite).

Implementa ports.RideRepository. Es el único sitio donde hay SQL.
Ningún otro microservicio accede a esta base de datos.
"""

import os
import sqlite3

from ..domain.model import Ride, RideStatus


def db_path() -> str:
    return os.getenv("DB_PATH", "rides.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=5)
    conn.row_factory = sqlite3.Row  # para leer las columnas por nombre
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rides (
                ride_id          TEXT PRIMARY KEY,
                user_id          TEXT NOT NULL,
                vehicle_id       TEXT NOT NULL,
                reservation_id   TEXT,
                origin_zone      TEXT NOT NULL,
                destination_zone TEXT,
                status           TEXT NOT NULL,   -- IN_PROGRESS | FINISHED
                started_at       TEXT NOT NULL,
                finished_at      TEXT,
                duration_min     REAL,
                cost             REAL,
                battery_level    INTEGER
            )
            """
        )


class SqliteRideRepository:
    def ping(self) -> None:
        """Comprueba que la base de datos responde (lo usa /health)."""
        with get_conn() as conn:
            conn.execute("SELECT 1")

    def save(self, ride: Ride) -> None:
        """Guarda un viaje. Si ya existía (mismo ride_id), lo sobrescribe."""
        with get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO rides (
                    ride_id, user_id, vehicle_id, reservation_id, origin_zone,
                    destination_zone, status, started_at, finished_at,
                    duration_min, cost, battery_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ride.ride_id,
                    ride.user_id,
                    ride.vehicle_id,
                    ride.reservation_id,
                    ride.origin_zone,
                    ride.destination_zone,
                    ride.status.value,
                    ride.started_at,
                    ride.finished_at,
                    ride.duration_min,
                    ride.cost,
                    ride.battery_level,
                ),
            )

    def get(self, ride_id: str) -> Ride | None:
        """Devuelve el viaje, o None si no existe."""
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM rides WHERE ride_id = ?", (ride_id,)).fetchone()
        if row is None:
            return None
        return Ride(**row)

    def list_rides(self, user_id: str | None = None, status: RideStatus | None = None) -> list[Ride]:
        """Lista viajes. Los filtros que lleguen como None no se aplican."""
        query = "SELECT * FROM rides WHERE 1 = 1"
        params = []
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY started_at DESC"
        with get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [Ride(**row) for row in rows]

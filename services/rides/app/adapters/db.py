"""Adaptador de salida: base de datos propia de rides (SQLite).

Ningún otro microservicio accede a esta base de datos.
Ejemplo: services/inventory/app/adapters/db.py
"""
import os
import sqlite3

from ..domain.model import Ride


def db_path():
    return os.getenv("DB_PATH", "ride.db")


def get_conn():
    conn = sqlite3.connect(db_path(), timeout=5)
    conn.row_factory = sqlite3.Row  # para leer las columnas por nombre
    return conn


def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rides (
            ride_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vehicle_id INTEGER NOT NULL,
            reservation_id INTEGER | None = None,
            origin_zone TEXT NOT NULL,
            destination_zone TEXT | None = None,
            status TEXT NOT NULL DEFAULT 'pending',
            started_at TEXT NOT NULL,
            finished_at TEXT | None = None,
            duration_min: float | None = None,
            cost: float | None = None,
            battery_level: int | None = None
        """)
    conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_events (
                    event_id     TEXT PRIMARY KEY,
                    processed_at TEXT NOT NULL
                )
                """
            )


class SqliteRideRepository:
    def ping(self):
        """Comprueba que la base de datos responde (lo usa /health)."""
        with get_conn() as conn:
            conn.execute("SELECT 1")

    def save(self, ride):
        """Guarda un ride. Si ya existía, lo sobrescribe."""
        with get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO rides (
                    ride_id, user_id, vehicle_id, reservation_id, origin_zone,
                    destination_zone, status, started_at, finished_at,
                    duration_min, cost, battery_level
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ride.ride_id, ride.user_id, ride.vehicle_id, ride.reservation_id, ride.origin_zone,
                    ride.destination_zone, ride.status.value, ride.started_at, ride.finished_at,
                    ride.duration_min, ride.cost, ride.battery_level
                )
            )

    def get(self, ride_id):
        """Devuelve el ride, o None si no existe."""
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM rides WHERE ride_id = ?", (ride_id,)).fetchone()
        if row is None:
            return None
        return Ride(**row)

    def list_rides(self, user_id=None, status=None):
        """Lista rides. Los filtros que lleguen como None no se aplican."""
        query = "SELECT * FROM rides WHERE 1 = 1"
        params = []
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        with get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [Ride(**row) for row in rows]

    def is_event_processed(self, event_id):
            """True si ese evento ya se aplicó antes."""
            with get_conn() as conn:
                row = conn.execute("SELECT 1 FROM processed_events WHERE event_id = ?", (event_id,)).fetchone()
            return row is not None
    
    def mark_event_processed(self, event_id, processed_at):
        """Apunta que el evento ya se aplicó."""
        with get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_events VALUES (?, ?)",
                (event_id, processed_at),
            )    

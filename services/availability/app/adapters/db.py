"""Adaptador de salida: base de datos propia de availability (SQLite).

Es el único archivo con SQL. Ningún otro microservicio accede a esta base de datos.

Tablas:
- vehicles: la ficha de cada vehículo (estado, zona, batería).
- processed_events: los event_id ya procesados, para no aplicar dos veces
  el mismo evento si SQS lo entrega repetido (idempotencia).
"""

import os
import sqlite3

from ..domain.model import Vehicle


def db_path():
    return os.getenv("DB_PATH", "availability.db")


def get_conn():
    conn = sqlite3.connect(db_path(), timeout=5)
    conn.row_factory = sqlite3.Row  # para leer las columnas por nombre
    return conn


def init_db():
    """Crea las tablas si no existen. Se llama al arrancar el servicio."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id    TEXT PRIMARY KEY,
                vehicle_type  TEXT NOT NULL,     -- BIKE | SCOOTER
                zone_id       TEXT NOT NULL,
                status        TEXT NOT NULL,     -- AVAILABLE, RESERVED, IN_USE...
                battery_level INTEGER,
                updated_at    TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id     TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            )
            """
        )


class SqliteVehicleRepository:
    def ping(self):
        """Comprueba que la base de datos responde (lo usa /health)."""
        with get_conn() as conn:
            conn.execute("SELECT 1")

    def save(self, vehicle):
        """Guarda un vehículo. Si ya existía, lo sobrescribe."""
        with get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO vehicles VALUES (?, ?, ?, ?, ?, ?)",
                (
                    vehicle.vehicle_id,
                    vehicle.vehicle_type.value,
                    vehicle.zone_id,
                    vehicle.status.value,
                    vehicle.battery_level,
                    vehicle.updated_at,
                ),
            )

    def get(self, vehicle_id):
        """Devuelve el vehículo, o None si no existe."""
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,)).fetchone()
        if row is None:
            return None
        return Vehicle(**dict(row))

    def list_vehicles(self, zone_id=None, vehicle_type=None, status=None):
        """Lista vehículos. Los filtros que lleguen como None no se aplican."""
        query = "SELECT * FROM vehicles WHERE 1 = 1"
        params = []
        if zone_id is not None:
            query += " AND zone_id = ?"
            params.append(zone_id)
        if vehicle_type is not None:
            query += " AND vehicle_type = ?"
            params.append(vehicle_type.value)
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        with get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [Vehicle(**dict(row)) for row in rows]

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
"""Adaptador de salida: base de datos propia de profiles (SQLite).

Implementa ports.ProfileRepository. Es el único sitio donde hay SQL.

Ningún otro microservicio accede a esta base de datos: si necesitan datos de
un perfil, llaman a la API de profiles.
"""

import os
import sqlite3

from ..domain.model import Profile, VehicleType
from ..ports.ports import ProfileRepository


def db_path() -> str:
    return os.getenv("DB_PATH", "profiles.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=5)
    conn.row_factory = sqlite3.Row  # para leer las columnas por nombre
    return conn


def init_db() -> None:
    """Crea la tabla si no existe. Se llama al arrancar el servicio."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id                 TEXT PRIMARY KEY,
                name                    TEXT NOT NULL,
                email                   TEXT NOT NULL,
                phone_number            TEXT,
                preferred_vehicle_type  TEXT,              -- BIKE | SCOOTER | NULL
                active                  INTEGER NOT NULL,  -- 1 activo, 0 baja lógica
                created_at              TEXT NOT NULL,
                updated_at              TEXT NOT NULL
            )
            """
        )


def _vehicle_type(profile: Profile) -> str | None:
    """Guarda el enum como texto (BIKE / SCOOTER) o NULL si no hay preferencia."""
    if profile.preferred_vehicle_type is None:
        return None
    return VehicleType(profile.preferred_vehicle_type).value


def _row_to_profile(row) -> Profile:
    data = dict(row)
    data["active"] = bool(data["active"])
    return Profile(**data)


class SqliteProfileRepository(ProfileRepository):
    def ping(self) -> None:
        with get_conn() as conn:
            conn.execute("SELECT 1")

    def get_profile(self, user_id: str) -> Profile | None:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
        return _row_to_profile(row) if row else None

    def save(self, profile: Profile) -> None:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    profile.user_id,
                    profile.name,
                    profile.email,
                    profile.phone_number,
                    _vehicle_type(profile),
                    int(profile.active),
                    profile.created_at,
                    profile.updated_at,
                ),
            )

    def update(self, profile: Profile) -> None:
        with get_conn() as conn:
            conn.execute(
                """
                UPDATE profiles
                SET name = ?, phone_number = ?, preferred_vehicle_type = ?,
                    active = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    profile.name,
                    profile.phone_number,
                    _vehicle_type(profile),
                    int(profile.active),
                    profile.updated_at,
                    profile.user_id,
                ),
            )
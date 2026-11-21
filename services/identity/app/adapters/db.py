"""Adaptador de salida: base de datos propia de identity (SQLite).

Ningún otro microservicio accede a esta base de datos.
Ejemplo: services/inventory/app/adapters/db.py
"""

import os

import sqlite3

from services.identity.app.domain.model import User, User_type

def db_path():
    return os.getenv("DB_PATH", "identity.db")


def get_conn():
    conn = sqlite3.connect(db_path(), timeout=5)
    conn.row_factory = sqlite3.Row  # para leer las columnas por nombre
    return conn


def init_db():
    """Crea las tablas si no existen. Se llama al arrancar el servicio."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id       TEXT PRIMARY KEY,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                type          TEXT NOT NULL,  -- USER | ADMIN | MAINTENANCE
                created_at    TEXT NOT NULL
            )
            """
        )


class SqliteUserRepository:
    def __init__(self, db_path):
        self.db_path = db_path

    def ping(self):
        """Comprueba que la base de datos funciona."""
        with get_conn() as conn:
            conn.execute("SELECT 1")

    def save(self, user):
        """Guarda un usuario en la base de datos."""
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, email, password_hash, type, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user.user_id, user.email, user.password_hash, user.type.value, user.created_at),
            )

    def get_user(self, user_id):
        """Busca un usuario por su id. Devuelve None si no existe."""
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row is None:
                return None
            return User(
                user_id=row["user_id"],
                email=row["email"],
                password_hash=row["password_hash"],
                type=User_type(row["type"]),
                created_at=row["created_at"],
            )
        

    def get_by_email(self, email):
        """Busca un usuario por su email. Devuelve None si no existe."""
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row is None:
                return None
            return User(
                user_id=row["user_id"],
                email=row["email"],
                password_hash=row["password_hash"],
                type=User_type(row["type"]),
                created_at=row["created_at"],
            )
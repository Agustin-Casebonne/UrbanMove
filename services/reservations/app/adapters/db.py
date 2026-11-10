"""Adaptador de salida: base de datos propia de reservations (SQLite).

Implementa ports.ReservationRepository. Es el único sitio donde hay SQL.
Ningún otro microservicio accede a esta base de datos.

CÓMO SE EVITA LA DOBLE RESERVA
Dos índices únicos PARCIALES: solo cuentan las filas con estado activo
(PENDING o CONFIRMED). Así:
- Un vehículo puede tener muchas reservas antiguas (canceladas, expiradas...),
  pero como mucho UNA activa.
- Si dos usuarios reservan el mismo vehículo a la vez, la base de datos
  acepta el primer INSERT y rechaza el segundo con IntegrityError. No hace
  falta "comprobar y luego insertar", que tendría una carrera entre ambos pasos.

Los cambios de estado usan UPDATE ... WHERE status IN (...): si una cancelación
y una expiración llegan a la vez, solo una de las dos cambia la fila.
"""

import os
import sqlite3

from ..domain.model import (
    Reservation,
    ReservationStatus,
    UserAlreadyHasReservation,
    VehicleAlreadyReserved,
)


def db_path() -> str:
    return os.getenv("DB_PATH", "reservations.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                reservation_id TEXT PRIMARY KEY,
                user_id        TEXT NOT NULL,
                vehicle_id     TEXT NOT NULL,
                vehicle_type   TEXT NOT NULL,      -- BIKE | SCOOTER
                zone_id        TEXT NOT NULL,
                status         TEXT NOT NULL,      -- PENDING | CONFIRMED | FULFILLED | CANCELLED | EXPIRED
                created_at     TEXT NOT NULL,
                expires_at     TEXT NOT NULL,
                updated_at     TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_reservation_per_vehicle
            ON reservations (vehicle_id) WHERE status IN ('PENDING', 'CONFIRMED')
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_reservation_per_user
            ON reservations (user_id) WHERE status IN ('PENDING', 'CONFIRMED')
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status_expires ON reservations (status, expires_at)")


def _row_to_reservation(row) -> Reservation:
    return Reservation(**dict(row))


ACTIVE_SQL = "('PENDING', 'CONFIRMED')"


class SqliteReservationRepository:
    def ping(self) -> None:
        with get_conn() as conn:
            conn.execute("SELECT 1")

    def create(self, reservation: Reservation) -> None:
        try:
            with get_conn() as conn:
                conn.execute(
                    "INSERT INTO reservations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        reservation.reservation_id,
                        reservation.user_id,
                        reservation.vehicle_id,
                        reservation.vehicle_type.value,
                        reservation.zone_id,
                        reservation.status.value,
                        reservation.created_at,
                        reservation.expires_at,
                        reservation.updated_at,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            # El mensaje de SQLite dice qué columna violó el índice único.
            if "vehicle_id" in str(exc):
                raise VehicleAlreadyReserved(reservation.vehicle_id) from exc
            if "user_id" in str(exc):
                raise UserAlreadyHasReservation(reservation.user_id) from exc
            raise

    def get(self, reservation_id: str) -> Reservation | None:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM reservations WHERE reservation_id = ?", (reservation_id,)
            ).fetchone()
        return _row_to_reservation(row) if row else None

    def list_reservations(
        self, user_id: str | None = None, status: ReservationStatus | None = None
    ) -> list[Reservation]:
        query = "SELECT * FROM reservations WHERE 1 = 1"
        params: list[str] = []
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY created_at DESC"
        with get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_reservation(r) for r in rows]

    def list_overdue(self, now_iso: str) -> list[Reservation]:
        with get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM reservations WHERE status IN {ACTIVE_SQL} AND expires_at <= ?",
                (now_iso,),
            ).fetchall()
        return [_row_to_reservation(r) for r in rows]

    def transition(
        self,
        reservation_id: str,
        from_statuses: tuple[ReservationStatus, ...],
        to_status: ReservationStatus,
        updated_at: str,
        expires_at: str | None = None,
    ) -> bool:
        placeholders = ", ".join("?" for _ in from_statuses)
        with get_conn() as conn:
            cur = conn.execute(
                f"""
                UPDATE reservations
                SET status = ?, updated_at = ?, expires_at = COALESCE(?, expires_at)
                WHERE reservation_id = ? AND status IN ({placeholders})
                """,
                (to_status.value, updated_at, expires_at, reservation_id, *[s.value for s in from_statuses]),
            )
        return cur.rowcount > 0

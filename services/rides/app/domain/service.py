"""Lógica de negocio de rides.

Solo depende del modelo y de los puertos: no sabe que existen FastAPI,
SQLite ni SNS.

Reglas:
- Solo se puede iniciar un viaje si availability dice que el vehículo
  está AVAILABLE o RESERVED.
- Al finalizar se calcula la duración y el coste preliminar.
- Finalizar es idempotente: si el viaje ya estaba FINISHED se devuelve
  tal cual y NO se publica otro RideFinished.
"""

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from ..ports.ports import AvailabilityChecker, EventPublisher, RideRepository
from .model import Ride, RideNotFound, RideStatus

UNLOCK_FEE = 0.50  # euros por desbloquear
PRICE_PER_MIN = 0.15  # euros por minuto


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


class RideService:
    def __init__(
        self,
        ride_repository: RideRepository,
        availability_checker: AvailabilityChecker | None,
        event_publisher: EventPublisher,
        clock: Callable[[], datetime] = utc_now,
    ):
        self.ride_repository = ride_repository
        self.availability_checker = availability_checker
        self.event_publisher = event_publisher
        self.clock = clock

    def check_health(self) -> None:
        """Comprueba que todos los puertos responden (lo usa /health)."""
        self.ride_repository.ping()

    def get_ride(self, ride_id: str) -> Ride:
        """Devuelve un viaje por su ride_id. Lanza RideNotFound si no existe."""
        ride = self.ride_repository.get(ride_id)
        if ride is None:
            raise RideNotFound(f"Ride {ride_id} not found")
        return ride

    def list_rides(self, user_id: str | None = None, status: RideStatus | None = None) -> list[Ride]:
        """Lista viajes. Los filtros que lleguen como None no se aplican."""
        return self.ride_repository.list_rides(user_id=user_id, status=status)

    def start_ride(
        self, user_id: str, vehicle_id: str, origin_zone: str, reservation_id: str | None = None
    ) -> Ride:
        if self.availability_checker is not None:
            self.availability_checker.check_vehicle(vehicle_id)

        ride = Ride(
            ride_id=str(uuid.uuid4()),
            user_id=user_id,
            vehicle_id=vehicle_id,
            reservation_id=reservation_id,
            origin_zone=origin_zone,
            status=RideStatus.IN_PROGRESS,
            started_at=to_iso(self.clock()),
        )
        self.ride_repository.save(ride)

        # 3. Avisar al resto del sistema (availability pondrá el vehículo en IN_USE)
        self.event_publisher.publish(
            "RideStarted",
            {
                "ride_id": ride.ride_id,
                "user_id": ride.user_id,
                "vehicle_id": ride.vehicle_id,
                "reservation_id": ride.reservation_id,
                "origin_zone": ride.origin_zone,
                "started_at": ride.started_at,
            },
        )
        return ride

    def finish_ride(self, ride_id: str, destination_zone: str, battery_level: int | None = None) -> Ride:
        ride = self.get_ride(ride_id)

        # Idempotencia: si ya terminó, no se repite nada
        if ride.status == RideStatus.FINISHED:
            return ride

        # Calcular duración y coste
        finished = self.clock()
        started = datetime.fromisoformat(ride.started_at)
        duration_min = round((finished - started).total_seconds() / 60, 2)
        cost = round(UNLOCK_FEE + PRICE_PER_MIN * duration_min, 2)

        ride.destination_zone = destination_zone
        ride.finished_at = to_iso(finished)
        ride.duration_min = duration_min
        ride.cost = cost
        ride.battery_level = battery_level
        ride.status = RideStatus.FINISHED
        self.ride_repository.save(ride)

        self.event_publisher.publish(
            "RideFinished",
            {
                "ride_id": ride.ride_id,
                "user_id": ride.user_id,
                "vehicle_id": ride.vehicle_id,
                "origin_zone": ride.origin_zone,
                "destination_zone": ride.destination_zone,
                "duration_min": ride.duration_min,
                "cost": ride.cost,
                "battery_level": ride.battery_level,
            },
        )
        return ride

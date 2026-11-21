"""Puertos de rides: contratos que el dominio necesita del exterior."""

from typing import Protocol

from ..domain.model import Ride, RideStatus


class RideRepository(Protocol):
    def ping(self) -> None: ...

    def save(self, ride: Ride) -> None: ...

    def get(self, ride_id: str) -> Ride | None: ...

    def list_rides(self, user_id: str | None = None, status: RideStatus | None = None) -> list[Ride]: ...


class EventPublisher(Protocol):
    def publish(self, event_type: str, data: dict) -> None: ...


class AvailabilityChecker(Protocol):
    def check_vehicle(self, vehicle_id: str) -> None: ...

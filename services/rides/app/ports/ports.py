"""Puertos de rides: contratos que el dominio necesita del exterior."""

from abc import ABC, abstractmethod

from ..domain.model import Ride, RideStatus


class RideRepository(ABC):
    @abstractmethod
    def ping(self) -> None: ...

    @abstractmethod
    def save(self, ride: Ride) -> None: ...

    @abstractmethod
    def get(self, ride_id: str) -> Ride | None: ...

    @abstractmethod
    def list_rides(self, user_id: str | None = None, status: RideStatus | None = None) -> list[Ride]: ...


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event_type: str, data: dict) -> None: ...


class AvailabilityChecker(ABC):
    @abstractmethod
    def check_vehicle(self, vehicle_id: str) -> None: ...

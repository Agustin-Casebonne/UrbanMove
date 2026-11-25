"""Lógica de negocio de availability.

Solo usa domain/model.py y los puertos: no sabe que existen FastAPI,
SQLite ni SNS.

Qué hace:
- Registrar vehículos nuevos (llegan con el evento VehiclePurchased).
- Cambiar el estado de un vehículo respetando ALLOWED_TRANSITIONS.
- Recibir la batería de un vehículo y avisar si está baja (VehicleBatteryLow).
- Aplicar los eventos que llegan de la cola (handle_event).
"""

import logging
from datetime import datetime, timezone

from .domain.model import (
    InvalidTransition,
    Vehicle,
    VehicleNotFound,
    VehicleStatus,
    VehicleType,
    can_transition,
)

logger = logging.getLogger("availability")


def now_iso():
    """Fecha y hora actual en UTC, como texto."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AvailabilityService:
    def __init__(self, repository, publisher, low_battery_threshold=20):
        self.repository = repository  # dónde se guardan los vehículos (db.py)
        self.publisher = publisher  # quién publica los eventos (events.py)
        self.low_battery_threshold = low_battery_threshold  # % por debajo del cual es "batería baja"

    def check_health(self):
        self.repository.ping()

    # ---------- consultas ----------

    def get_vehicle(self, vehicle_id):
        vehicle = self.repository.get(vehicle_id)
        if vehicle is None:
            raise VehicleNotFound(vehicle_id)
        return vehicle

    def list_vehicles(self, zone_id=None, vehicle_type=None, status=None):
        return self.repository.list_vehicles(zone_id=zone_id, vehicle_type=vehicle_type, status=status)

    # ---------- comandos ----------

    def register_vehicle(self, vehicle_id, vehicle_type, zone_id):
        """Da de alta un vehículo nuevo como AVAILABLE. Si ya existía, lo deja como está."""
        existing = self.repository.get(vehicle_id)
        if existing is not None:
            return existing

        vehicle = Vehicle(
            vehicle_id=vehicle_id,
            vehicle_type=VehicleType(vehicle_type),
            zone_id=zone_id,
            status=VehicleStatus.AVAILABLE,
            battery_level=100,
            updated_at=now_iso(),
        )
        self.repository.save(vehicle)
        return vehicle

    def transition(self, vehicle_id, new_status, zone_id=None, battery_level=None):
        """Cambia el estado de un vehículo si la regla lo permite.

        Opcionalmente actualiza también la zona y la batería.
        """
        vehicle = self.get_vehicle(vehicle_id)
        new_status = VehicleStatus(new_status)

        if not can_transition(vehicle.status, new_status):
            raise InvalidTransition(vehicle_id, vehicle.status, new_status)

        vehicle.status = new_status
        if zone_id is not None:
            vehicle.zone_id = zone_id
        if battery_level is not None:
            vehicle.battery_level = battery_level
        vehicle.updated_at = now_iso()

        self.repository.save(vehicle)
        return vehicle

    def report_battery(self, vehicle_id, battery_level):
        """Telemetría: el vehículo informa de su batería.

        Si está AVAILABLE y la batería baja del umbral, pasa a LOW_BATTERY
        y se publica VehicleBatteryLow (lo escucha la Lambda de mantenimiento).
        """
        vehicle = self.get_vehicle(vehicle_id)
        vehicle.battery_level = battery_level
        vehicle.updated_at = now_iso()

        is_low = battery_level < self.low_battery_threshold
        if is_low and vehicle.status == VehicleStatus.AVAILABLE:
            vehicle.status = VehicleStatus.LOW_BATTERY
            self.repository.save(vehicle)  # primero se guarda, después se publica
            self.publisher.publish(
                "VehicleBatteryLow",
                {
                    "vehicle_id": vehicle.vehicle_id,
                    "battery_level": battery_level,
                    "zone_id": vehicle.zone_id,
                },
            )
        else:
            self.repository.save(vehicle)
        return vehicle

    def relocate(self, vehicle_id, zone_id):
        """Cambia la zona del vehículo sin tocar su estado (recolocación)."""
        vehicle = self.get_vehicle(vehicle_id)
        vehicle.zone_id = zone_id
        vehicle.updated_at = now_iso()
        self.repository.save(vehicle)
        return vehicle

    # ---------- eventos que llegan de la cola ----------

    def handle_event(self, event):
        """Aplica un evento recibido de la cola SQS.

        - Si el evento ya se procesó antes (mismo event_id), no hace nada.
        - Si el evento no encaja con el estado actual (por ejemplo, llega
          desordenado), se registra en el log y se descarta, para que no
          se reintente sin fin ni acabe en la DLQ.

        Devuelve True si el evento se aplicó y False si se ignoró.
        """
        event_id = event["event_id"]
        event_type = event["event_type"]
        data = event["data"]

        if self.repository.is_event_processed(event_id):
            logger.info(f"evento {event_id} ya procesado, se ignora")
            return False

        try:
            self._apply_event(event_type, data)
            applied = True
        except (InvalidTransition, VehicleNotFound) as exc:
            logger.warning(f"evento {event_type} {event_id} descartado: {exc}")
            applied = False

        self.repository.mark_event_processed(event_id, now_iso())
        return applied

    def _apply_event(self, event_type, data):
        """Qué hacer con cada tipo de evento (tabla de docs/eventos.md)."""
        if event_type == "VehiclePurchased":
            self.register_vehicle(data["vehicle_id"], data["vehicle_type"], data["initial_zone"])

        elif event_type == "VehicleReserved":
            self.transition(data["vehicle_id"], VehicleStatus.RESERVED)

        elif event_type in ("ReservationCancelled", "ReservationExpired"):
            self.transition(data["vehicle_id"], VehicleStatus.AVAILABLE)

        elif event_type == "RideStarted":
            self.transition(data["vehicle_id"], VehicleStatus.IN_USE)

        elif event_type == "RideFinished":
            battery = data.get("battery_level")
            if battery is not None and battery < self.low_battery_threshold:
                new_status = VehicleStatus.LOW_BATTERY
            else:
                new_status = VehicleStatus.AVAILABLE
            # No se publica VehicleBatteryLow aquí: la Lambda de mantenimiento
            # ya escucha RideFinished y mira su battery_level.
            self.transition(
                data["vehicle_id"], new_status, zone_id=data["destination_zone"], battery_level=battery
            )

        elif event_type == "VehicleWithdrawnForMaintenance":
            self.transition(data["vehicle_id"], VehicleStatus.WITHDRAWN)
            # El tipo de orden de maintenance decide a qué estado pasa después de retirarlo.
            if data.get("type") == "CHARGE":
                self.transition(data["vehicle_id"], VehicleStatus.CHARGING)
            elif data.get("type") == "REPAIR":
                self.transition(data["vehicle_id"], VehicleStatus.REPAIRING)

        elif event_type == "VehicleReturnedToService":
            # Según las reglas, solo se vuelve a AVAILABLE desde READY_FOR_SERVICE.
            vehicle = self.get_vehicle(data["vehicle_id"])
            if vehicle.status != VehicleStatus.READY_FOR_SERVICE:
                self.transition(data["vehicle_id"], VehicleStatus.READY_FOR_SERVICE)
            self.transition(data["vehicle_id"], VehicleStatus.AVAILABLE, zone_id=data.get("zone_id"))

        elif event_type == "RelocationOrderCompleted":
            for vehicle_id in data["vehicle_ids"]:
                self.relocate(vehicle_id, data["to_zone"])

        else:
            # Eventos que no le interesan a availability (UserRegistered...)
            logger.info(f"evento {event_type} ignorado: no afecta a availability")

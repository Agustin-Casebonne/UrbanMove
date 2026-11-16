"""Adaptador de salida: consulta al microservicio availability por HTTP.

Implementa ports.AvailabilityChecker. Solo se usa si está definida la
variable de entorno AVAILABILITY_URL (ver main.py).

Contrato esperado de availability:
    GET {AVAILABILITY_URL}/vehicles/{vehicle_id}
    200 -> {"vehicle_id": "...", "status": "AVAILABLE" | "RESERVED" | ...}
    404 -> el vehículo no existe

Tolerancia a fallos: la llamada tiene un timeout corto. Si availability no
responde, se lanza AvailabilityServiceDown (la API devuelve 503) en vez de
dejar al usuario esperando indefinidamente. Se reenvía el X-Correlation-ID
para poder seguir la petición en los logs de ambos servicios.
"""

import json
import urllib.error
import urllib.request

from urbanmove_common.logging_utils import CORRELATION_HEADER, get_correlation_id

from ..domain.model import AvailabilityServiceDown, VehicleNotAvailable, VehicleNotFound


class HttpAvailabilityChecker:
    def __init__(self, base_url: str, timeout_seconds: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    def check_vehicle(self, vehicle_id: str) -> None:
        request = urllib.request.Request(
            f"{self.base_url}/vehicles/{vehicle_id}",
            headers={CORRELATION_HEADER: get_correlation_id()},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise VehicleNotFound(vehicle_id) from exc
            raise AvailabilityServiceDown(f"availability respondió {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise AvailabilityServiceDown(str(exc)) from exc

        status = body.get("status")
        if status != "AVAILABLE":
            raise VehicleNotAvailable(f"{vehicle_id} está en estado {status}")

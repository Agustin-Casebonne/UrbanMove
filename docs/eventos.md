# Contrato de eventos de UrbanMove

Todos los eventos se publican en el tópico SNS **`urbanmove-events`**. Desde ahí se reparten a una cola SQS por consumidor (`urbanmove-history`, `urbanmove-availability`, `urbanmove-datalake-ingest`, `urbanmove-maintenance-detector`). Los mensajes que fallan 3 veces van a la dead-letter queue **`urbanmove-dlq`**.

El código que construye y publica los eventos está en `shared/urbanmove_common/events.py`.

## 1. Envoltura común (obligatoria en todos los eventos)

```json
{
  "event_id": "5b0d6f0e-8a1c-4c6e-9a51-1f7f1f0f2a11",
  "event_type": "RideStarted",
  "schema_version": 1,
  "source": "rides",
  "timestamp": "2026-10-15T12:00:00+00:00",
  "correlation_id": "c0a8012e-1234-4b6a-9f00-abcdef123456",
  "data": { }
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `event_id` | string (UUID) | Identificador único. Los consumidores lo usan para **idempotencia**: si ya procesaron ese `event_id`, lo ignoran. |
| `event_type` | string | Uno de los tipos de la tabla de abajo. |
| `schema_version` | int | Versión del esquema de `data`. Si cambia el contenido, se sube la versión. |
| `source` | string | Microservicio productor (nombre de la carpeta en `services/`). |
| `timestamp` | string (ISO 8601, UTC) | Momento en que ocurrió el hecho. |
| `correlation_id` | string | Mismo valor que la cabecera `X-Correlation-ID` de la petición original. Permite seguir un flujo completo. |
| `data` | object | Contenido específico de cada evento. |

## 2. Catálogo de eventos

| Evento | Productor | Consumidores | Campos mínimos de `data` |
|---|---|---|---|
| `UserRegistered` | profiles | history, datalake | `user_id`, `email`, `registered_at` |
| `VehiclePurchased` | inventory | availability, history, datalake | `vehicle_id`, `vehicle_type`, `model`, `purchase_date`, `initial_zone` |
| `VehicleReserved` | reservations | availability, history, datalake, Lambda expiración | `reservation_id`, `user_id`, `vehicle_id`, `zone_id`, `expires_at` |
| `ReservationCancelled` | reservations | availability, history, datalake | `reservation_id`, `user_id`, `vehicle_id` |
| `ReservationExpired` | reservations (vía Lambda) | availability, history, datalake | `reservation_id`, `user_id`, `vehicle_id` |
| `RideStarted` | rides | availability, history, datalake | `ride_id`, `user_id`, `vehicle_id`, `vehicle_type`, `origin_zone`, `started_at` |
| `RideFinished` | rides | availability, history, datalake | `ride_id`, `user_id`, `vehicle_id`, `origin_zone`, `destination_zone`, `duration_min`, `cost`, `battery_level` |
| `VehicleBatteryLow` | availability (telemetría) | Lambda detección mantenimiento, history, datalake | `vehicle_id`, `battery_level`, `zone_id` |
| `VehicleWithdrawnForMaintenance` | maintenance | availability, history, datalake | `order_id`, `vehicle_id`, `reason` (`CHARGE` / `REPAIR` / `REVIEW`) |
| `VehicleReturnedToService` | maintenance | availability, history, datalake | `order_id`, `vehicle_id`, `zone_id` |
| `DemandHotspotDetected` | Lambda recolocación / analytics | relocation, history, datalake | `zone_id`, `available`, `demand_last_hour`, `vehicle_type` |
| `RelocationOrderCreated` | relocation | history, datalake | `order_id`, `from_zone`, `to_zone`, `vehicle_type`, `quantity` |
| `RelocationOrderCompleted` | relocation | availability, history, datalake | `order_id`, `from_zone`, `to_zone`, `vehicle_ids`, `delay_min` |

## 3. Ejemplo completo

```json
{
  "event_id": "b5f16015-1a92-48d4-86da-1944cb08d77d",
  "event_type": "VehiclePurchased",
  "schema_version": 1,
  "source": "inventory",
  "timestamp": "2026-10-15T12:47:13.304394+00:00",
  "correlation_id": "demo-1",
  "data": {
    "vehicle_id": "B-3c47b800",
    "vehicle_type": "BIKE",
    "model": "Orbea",
    "purchase_date": "2026-09-01",
    "initial_zone": "Z01",
    "admin_status": "ACTIVE",
    "created_at": "2026-10-15T12:47:13.301955+00:00"
  }
}
```

## 4. Reglas para productores y consumidores

- **Productor:** guarda primero en su base de datos y después publica el evento. Si el bus falla, reintenta 3 veces y, si sigue fallando, guarda el evento en el *outbox* local (`outbox.jsonl`) para reenviarlo. La operación del usuario no falla por culpa del bus.
- **Consumidor:** debe ser **idempotente**. Guarda los `event_id` procesados y descarta duplicados.
- **Errores:** si un consumidor no puede procesar un mensaje, no lo borra de la cola. SQS lo reintenta y, tras 3 fallos, lo mueve a `urbanmove-dlq` para revisarlo.

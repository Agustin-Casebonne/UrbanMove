# Lambdas

Una carpeta por función. Se despliegan en LocalStack y se conectan a las colas SQS creadas en `infra/localstack/init-aws.sh`.

| Lambda | Disparador | Qué hace |
|---|---|---|
| `reservation_expiration` (obligatoria) | Programada cada minuto | Busca reservas no confirmadas que han caducado y llama a `reservations` para expirarlas (publica `ReservationExpired`). |
| `maintenance_detector` (obligatoria) | Cola `urbanmove-maintenance-detector` | Si llega `VehicleBatteryLow` o un `RideFinished` con batería baja o demasiados usos, crea una orden en `maintenance`. |
| `datalake_ingest` (obligatoria) | Cola `urbanmove-datalake-ingest` | Guarda cada evento en `s3://urbanmove-datalake/raw/...` y la versión validada en `trusted/...`. |
| `datamart_builder` (ampliación) | Programada | Lee `trusted/` y genera los data marts en `curated/`. |
| `relocation` (ampliación) | Programada | Lee el data mart de demanda y crea órdenes de recolocación. |

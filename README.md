# UrbanMove

Sistema distribuido de movilidad urbana (bicicletas y patinetes eléctricos). Proyecto de grupo de **Tecnologías de Servicios para Ciencia de Datos** (Grado en Ciencia e Ingeniería de Datos, ULPGC).

## Tecnologías

| Pieza | Tecnología |
|---|---|
| Microservicios | Python 3.12 + FastAPI (OpenAPI automático en `/docs`) |
| Base de datos | SQLite, una por microservicio (cada servicio es dueño de sus datos) |
| Bus de eventos | SNS + SQS (con dead-letter queue) en LocalStack |
| Data Lake | S3 en LocalStack: `raw/`, `trusted/`, `curated/` |
| Lambdas | Python en LocalStack |
| Despliegue local | Docker Compose |
| CI | GitHub Actions: ruff, pytest y docker build |

## Estructura del repositorio

```
services/      un directorio por microservicio (app/, tests/, Dockerfile)
shared/        código común: formato de eventos y logs con correlation id
lambdas/       funciones serverless
apps/          app de usuarios, app de mantenimiento y dashboard
infra/         docker-compose.yml y script de LocalStack
docs/          arquitectura, contratos de APIs y eventos, ADRs, evidencias
```

## Microservicios

| Servicio | Puerto local | Estado |
|---|---|---|
| identity | 8001 | esqueleto |
| profiles | 8002 | esqueleto |
| inventory | 8003 | **implementado** (plantilla de referencia) |
| availability | 8004 | esqueleto |
| reservations | 8005 | esqueleto |
| rides | 8006 | esqueleto |
| history | 8007 | esqueleto |
| maintenance | 8008 | esqueleto |
| relocation | 8009 | esqueleto |
| analytics | 8010 | esqueleto |

Documentación interactiva de cada API: `http://localhost:<puerto>/docs`

## Cómo levantarlo en local

Requisitos: Docker Desktop.

```bash
docker compose -f infra/docker-compose.yml up --build
```

Esto arranca LocalStack (crea el tópico SNS, las colas SQS, la DLQ y el bucket del Data Lake) y los 10 microservicios.


## Almacenamiento de eventos

<img width="638" height="602" alt="image" src="https://github.com/user-attachments/assets/d8e8cfde-7cd0-4319-ac79-ee1c2ea2a4eb" />


## Contenedores

<img width="785" height="333" alt="image" src="https://github.com/user-attachments/assets/4f5cdc89-6f61-4250-b562-8e667e038c24" />



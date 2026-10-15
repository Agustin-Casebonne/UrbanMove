"""Genera el esqueleto de un microservicio nuevo copiando la estructura de inventory.

Uso (desde la raíz del repo):
    python scripts/new_service.py <nombre> "<descripción>"

Crea services/<nombre>/ con app/main.py (endpoint /health), Dockerfile,
requirements.txt y un test. Luego solo hay que añadir la lógica propia.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MAIN = '''"""Microservicio {title}.

Responsabilidad: {description}

TODO:
{todo}
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from urbanmove_common.logging_utils import add_correlation_middleware, get_logger

SERVICE_NAME = "{name}"
logger = get_logger(SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aquí se inicializa la base de datos propia del servicio (ver services/inventory/app/db.py)
    yield


app = FastAPI(
    title="UrbanMove - {title}",
    version="0.1.0",
    description="{description}",
    lifespan=lifespan,
)
add_correlation_middleware(app, logger)


@app.get("/health")
def health():
    return {{"status": "ok", "service": SERVICE_NAME}}
'''

TEST = """from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "{name}"
"""


def main(name: str, description: str, todo: list[str] | None = None) -> None:
    src = ROOT / "services" / "inventory"
    dst = ROOT / "services" / name
    if dst.exists():
        print(f"services/{name} ya existe, no se toca")
        return
    (dst / "app").mkdir(parents=True)
    (dst / "tests").mkdir()
    (dst / "app" / "__init__.py").write_text("")
    todo_text = "\n".join(f"- {t}" for t in (todo or ["Definir endpoints y eventos"]))
    (dst / "app" / "main.py").write_text(
        MAIN.format(name=name, title=name.capitalize(), description=description, todo=todo_text)
    )
    (dst / "tests" / f"test_{name}.py").write_text(TEST.format(name=name))
    (dst / "requirements.txt").write_text((src / "requirements.txt").read_text())
    (dst / "Dockerfile").write_text((src / "Dockerfile").read_text().replace("inventory", name))
    print(f"Creado services/{name}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])

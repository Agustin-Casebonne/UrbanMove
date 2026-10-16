from fastapi.testclient import TestClient

from app.main import app


# pytest la encuentra automáticamente y ejecuta la funcion test_health
def test_health():
    # Crear un cliente de prueba para la aplicación FastAPI y hacer una solicitud GET a la ruta /health
    with TestClient(app) as client:
        r = client.get("/health")
    # Verificar el status code y el contenido de la respuesta
    assert r.status_code == 200
    assert r.json()["service"] == "analytics"

import os

# Las pruebas nunca leen las credenciales de producción del archivo .env.
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "testing-only-random-like-secret-at-least-32-characters"
os.environ["AUTH_RATE_LIMIT"] = "false"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://gym:gym_test@localhost:5432/gym_test"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.cli import create_admin, seed_catalog
from app.core.database import Base, SessionFactory, engine, load_models
from app.core.security import issue_token
from app.main import app
from app.modules.users.schemas import Registration


@pytest.fixture
def client():
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip(
            "Integración requiere TEST_DATABASE_URL de PostgreSQL, se ejecuta en GitHub Actions."
        )
    if not engine.url.database.endswith("_test"):
        raise RuntimeError(
            "Las pruebas solo pueden borrar datos de una base cuyo nombre termine en _test."
        )
    load_models()
    with engine.begin() as connection:
        names = ", ".join(f'gym_app."{t.name}"' for t in Base.metadata.sorted_tables)
        connection.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    with SessionFactory.begin() as db:
        seed_catalog(db)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def member(client):
    data = {"nombre": "Alex Torres", "correo": "alex@example.com", "clave": "password-testing-123"}
    response = client.post("/auth/register", json=data)
    assert response.status_code == 201, response.text
    token = client.post(
        "/auth/login", json={"correo": data["correo"], "clave": data["clave"]}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch(
        "/me",
        headers=headers,
        json={"edad": 24, "talla_m": 1.75, "peso_kg": 80, "objetivo": "Ganar fuerza"},
    )
    assert response.status_code == 200, response.text
    return headers


@pytest.fixture
def admin(client):
    with SessionFactory.begin() as db:
        user = create_admin(
            db,
            Registration(
                nombre="Max Admin", correo="admin@example.com", clave="password-admin-123"
            ),
        )
        token = issue_token(user.id)
    return {"Authorization": f"Bearer {token}"}

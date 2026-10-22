import logging
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError, SQLAlchemyError

from app.core.diagnostics import report_internal_error
from app.core.errors import install_error_handlers

SECRET = "credencial-privada-no-debe-aparecer"
ORIGIN = "https://frontend.example.com"


class DriverError(Exception):
    sqlstate = "28P01"


@pytest.mark.parametrize(
    "error,status,event",
    [
        (
            OperationalError(
                f"SELECT '{SECRET}'",
                {"clave": SECRET},
                DriverError(f"password authentication failed postgresql://user:{SECRET}@host"),
            ),
            503,
            "database_unavailable",
        ),
        (
            IntegrityError("INSERT", {"clave": SECRET}, DriverError(SECRET)),
            409,
            "integrity_conflict",
        ),
        (
            ProgrammingError(SECRET, {"clave": SECRET}, DriverError(SECRET)),
            500,
            "persistence_error",
        ),
        (SQLAlchemyError(SECRET), 500, "persistence_error"),
        (RuntimeError(SECRET), 500, "unexpected_error"),
    ],
)
def test_errors_keep_status_cors_and_safe_operation_context(caplog, error, status, event):
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(CORSMiddleware, allow_origins=[ORIGIN], allow_methods=["POST"])

    @app.post("/errores/{item_id}")
    def fail(item_id: str):
        raise error

    # No se desactiva raise_server_exceptions: un fallo que escape haría fallar esta prueba.
    with TestClient(app) as client:
        response = client.post(
            f"/errores/{SECRET}?access_token={SECRET}",
            headers={"Origin": ORIGIN, "Authorization": f"Bearer {SECRET}"},
            json={"clave": SECRET},
        )

    assert response.status_code == status
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert set(response.json()) == {"detail"}
    records = [r for r in caplog.records if r.name == "fitanalytics.errors"]
    assert len(records) == 1
    assert f"event={event}" in records[0].getMessage()
    assert "operation=POST /errores/{item_id}" in records[0].getMessage()
    assert f"status={status}" in records[0].getMessage()
    assert records[0].levelno == (logging.WARNING if status == 409 else logging.ERROR)
    assert records[0].exc_info is None
    assert SECRET not in response.text + caplog.text
    assert "postgresql://" not in response.text + caplog.text


@pytest.mark.parametrize("status", [401, 403, 404])
def test_expected_http_errors_preserve_their_response_without_internal_error_logs(caplog, status):
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/protegido")
    def denied():
        raise HTTPException(status, "Acceso no disponible.", headers={"X-Expected": "yes"})

    with TestClient(app) as client:
        response = client.get("/protegido")

    assert response.status_code == status
    assert response.json() == {"detail": "Acceso no disponible."}
    assert response.headers["X-Expected"] == "yes"
    assert not [r for r in caplog.records if r.name == "fitanalytics.errors"]


class InputData(BaseModel):
    edad: int


def test_validation_errors_do_not_return_input_values_or_log_the_request(caplog):
    app = FastAPI()
    install_error_handlers(app)

    @app.post("/validar")
    def validate(data: InputData):
        return {"edad": data.edad}

    with TestClient(app) as client:
        response = client.post("/validar", json={"edad": SECRET, "clave": SECRET})

    assert response.status_code == 422
    assert set(response.json()["detail"][0]) == {"loc", "msg", "type"}
    assert SECRET not in response.text + caplog.text
    assert not [r for r in caplog.records if r.name == "fitanalytics.errors"]


def test_successful_requests_remain_unchanged(caplog):
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/disponible")
    def available():
        return {"status": "ok"}

    with TestClient(app) as client:
        response = client.get("/disponible")

    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert not [r for r in caplog.records if r.name == "fitanalytics.errors"]


def test_invalid_server_response_is_sanitized(caplog):
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/respuesta", response_model=InputData)
    def invalid_response():
        return {"edad": SECRET}

    with TestClient(app) as client:
        response = client.get("/respuesta")

    assert response.status_code == 500
    assert "error_type=ResponseValidationError" in caplog.text
    assert SECRET not in response.text + caplog.text


def test_failed_commit_rolls_back_and_never_reports_a_successful_save(monkeypatch, caplog):
    from app.core import database

    class FailedSession:
        rolled_back = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def commit(self):
            raise OperationalError("INSERT", {"clave": SECRET}, DriverError(SECRET))

        def rollback(self):
            self.rolled_back = True

    session = FailedSession()
    monkeypatch.setattr(database, "SessionFactory", lambda: session)
    app = FastAPI()
    install_error_handlers(app)

    @app.post("/guardar", status_code=201)
    def save(db: Annotated[object, Depends(database.get_db, scope="function")]):
        return {"guardado": True}

    with TestClient(app) as client:
        response = client.post("/guardar")

    assert response.status_code == 503
    assert session.rolled_back
    assert response.json() == {"detail": "La base de datos no está disponible. Intenta nuevamente."}
    assert SECRET not in response.text + caplog.text


def test_diagnostics_ignore_malformed_sqlstate(caplog):
    class Original(Exception):
        sqlstate = SECRET

    report_internal_error(ProgrammingError(SECRET, {"clave": SECRET}, Original(SECRET)))
    assert "sqlstate=sin_codigo" in caplog.text
    assert SECRET not in caplog.text

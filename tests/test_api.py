from datetime import timedelta

from sqlalchemy import func, select

from app.core.database import SessionFactory
from app.core.security import issue_token
from app.core.validation import business_today
from app.modules.admin.models import Auditoria


def session_payload(load=32, date=None):
    return {
        "fecha": (date or business_today()).isoformat(),
        "registros": [{"ejercicio_id": 1, "series": 3, "repeticiones": 8, "carga_kg": load}],
    }


def test_authentication_and_private_data(client, member):
    assert client.get("/health").status_code == 200
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.get("/admin/usuarios", headers=member).status_code == 403
    me = client.get("/me", headers=member).json()
    assert me["rol"] == "usuario" and me["activo"] and "clave_hash" not in me
    assert (
        client.post(
            "/auth/register",
            json={"nombre": "Other", "correo": "ALEX@example.com", "clave": "password-123"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/auth/register",
            json={
                "nombre": "Other",
                "correo": "other@example.com",
                "clave": "password-123",
                "rol": "admin",
            },
        ).status_code
        == 422
    )
    r = client.post(
        "/auth/register",
        json={"nombre": "Other User", "correo": "other@example.com", "clave": "password-123"},
    )
    token = client.post(
        "/auth/login", json={"correo": "other@example.com", "clave": "password-123"}
    ).json()["access_token"]
    client.post("/sesiones", headers=member, json=session_payload())
    assert client.get("/sesiones", headers={"Authorization": f"Bearer {token}"}).json() == []
    assert r.json()["perfil_completo"] is False


def test_session_transaction_and_progress(client, member):
    response = client.post("/sesiones", headers=member, json=session_payload())
    assert response.status_code == 201, response.text
    assert response.json()["volumen_kg"] == 768
    bad = session_payload()
    bad["registros"].append({"ejercicio_id": 999, "series": 3, "repeticiones": 8, "carga_kg": 20})
    assert client.post("/sesiones", headers=member, json=bad).status_code == 422
    assert len(client.get("/sesiones", headers=member).json()) == 1
    progress = client.get("/progreso", headers=member).json()
    assert progress["total_sesiones"] == 1 and progress["volumen_total_kg"] == 768
    assert progress["ultima_medicion"]["imc"] == 26.12
    assert isinstance(progress["puntos"][0]["volumen_kg"], (int, float))
    assert (
        client.get("/progreso?desde=2026-10-02&hasta=2026-10-01", headers=member).status_code == 422
    )
    assert client.get("/progreso?ejercicio_id=0", headers=member).status_code == 422


def test_prediction_and_stored_overview(client, member):
    first = client.post("/analisis", headers=member, json={"ejercicio_id": 1})
    assert first.json()["estado"] == "historial_insuficiente"
    for i in range(8):
        client.post(
            "/sesiones",
            headers=member,
            json=session_payload(32 + i * 2, business_today() - timedelta(weeks=7 - i)),
        )
    goal = client.post(
        "/metas", headers=member, json={"ejercicio_id": 1, "carga_objetivo_kg": 50}
    ).json()
    result = client.post(
        "/analisis", headers=member, json={"ejercicio_id": 1, "meta_id": goal["id"]}
    )
    assert result.status_code == 200, result.text
    assert result.json()["siguiente_carga_kg"] == 48
    overview = client.get("/inicio", headers=member).json()
    assert overview["ultimo_analisis"]["resultado"] == result.json()
    assert overview["rendimiento"][0]["sesiones"] == 8
    assert overview["metas"][0]["avance_porcentaje"] == 92
    assert (
        client.post(
            "/analisis", headers=member, json={"ejercicio_id": 2, "meta_id": goal["id"]}
        ).status_code
        == 404
    )


def test_administration_and_revocation(client, member, admin):
    assert client.get("/admin/resumen", headers=admin).status_code == 200
    me = client.get("/me", headers=admin).json()
    assert (
        client.patch(
            f"/admin/usuarios/{me['id']}", headers=admin, json={"rol": "usuario"}
        ).status_code
        == 409
    )
    created = client.post(
        "/admin/usuarios",
        headers=admin,
        json={
            "nombre": "Valeria Torres",
            "correo": "valeria@example.com",
            "clave": "password-123",
            "rol": "usuario",
        },
    )
    assert created.status_code == 201, created.text
    token = client.post(
        "/auth/login", json={"correo": "valeria@example.com", "clave": "password-123"}
    ).json()["access_token"]
    client.patch(f"/admin/usuarios/{created.json()['id']}", headers=admin, json={"activo": False})
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    assert (
        client.post(
            "/auth/login", json={"correo": "valeria@example.com", "clave": "password-123"}
        ).status_code
        == 401
    )
    assert client.post("/analisis", headers=admin, json={"ejercicio_id": 1}).status_code == 403
    assert (
        client.get("/admin/usuarios?q=valeria&estado=inactivo", headers=admin).json()["total"] == 1
    )
    assert client.get("/admin/usuarios?pagina=0", headers=admin).status_code == 422


def test_catalog_deactivation_delete_and_audit(client, member, admin):
    item = client.post("/sesiones", headers=member, json=session_payload()).json()
    goal = client.post(
        "/metas", headers=member, json={"ejercicio_id": 1, "carga_objetivo_kg": 30}
    ).json()
    assert goal["estado"] == "alcanzada"
    client.patch("/admin/ejercicios/1", headers=admin, json={"activo": False})
    assert all(e["id"] != 1 for e in client.get("/ejercicios", headers=member).json())
    assert len(client.get("/sesiones", headers=member).json()) == 1
    assert client.post("/sesiones", headers=member, json=session_payload()).status_code == 422
    assert client.delete(f"/admin/sesiones/{item['id']}", headers=admin).status_code == 204
    assert client.get("/progreso", headers=member).json()["total_sesiones"] == 0
    assert client.get("/metas", headers=member).json()[0]["estado"] == "pendiente"
    assert client.delete(f"/admin/metas/{goal['id']}", headers=admin).status_code == 204
    assert (
        client.post(
            "/admin/ejercicios",
            headers=admin,
            json={"nombre": "  PRESS   de banca ", "unidad": "kg"},
        ).status_code
        == 409
    )
    with SessionFactory() as db:
        assert db.scalar(select(func.count()).select_from(Auditoria)) >= 3


def test_current_role_is_checked_and_json_errors_do_not_echo_password(client, admin):
    user = client.post(
        "/admin/usuarios",
        headers=admin,
        json={
            "nombre": "Second Admin",
            "correo": "second@example.com",
            "clave": "password-123",
            "rol": "admin",
        },
    ).json()
    token = issue_token(user["id"])
    client.patch(f"/admin/usuarios/{user['id']}", headers=admin, json={"rol": "usuario"})
    assert (
        client.get("/admin/resumen", headers={"Authorization": f"Bearer {token}"}).status_code
        == 403
    )
    result = client.post(
        "/auth/register", json={"nombre": "Max123", "correo": "broken", "clave": "short"}
    )
    assert result.status_code == 422
    assert all("input" not in error and "ctx" not in error for error in result.json()["detail"])

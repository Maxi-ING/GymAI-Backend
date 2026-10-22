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
    assert result.json()["modelo_version"] == "lineal_comparable_v2"
    assert result.json()["repeticiones_analizadas"] == 8
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


def test_goals_and_predictions_respect_repetitions(client, member):
    for i in range(4):
        client.post(
            "/sesiones",
            headers=member,
            json=session_payload(30 + i * 2, business_today() - timedelta(weeks=3 - i)),
        )
    heavier = session_payload(100)
    heavier["registros"][0]["repeticiones"] = 3
    client.post("/sesiones", headers=member, json=heavier)
    response = client.post(
        "/metas",
        headers=member,
        json={"ejercicio_id": 1, "carga_objetivo_kg": 40, "repeticiones_objetivo": 8},
    )
    assert response.status_code == 201
    goal = response.json()
    assert goal["estado"] == "pendiente" and goal["repeticiones_objetivo"] == 8
    assert client.get("/metas", headers=member).json()[0]["estado"] == "pendiente"
    overview = client.get("/inicio", headers=member).json()["metas"][0]
    assert overview["ultima_carga_kg"] == 36 and overview["avance_porcentaje"] == 90
    result = client.post(
        "/analisis",
        headers=member,
        json={"ejercicio_id": 1, "meta_id": goal["id"], "repeticiones": 8},
    )
    assert result.status_code == 200 and result.json()["siguiente_carga_kg"] == 38
    assert (
        client.post(
            "/analisis",
            headers=member,
            json={"ejercicio_id": 1, "meta_id": goal["id"], "repeticiones": 3},
        ).status_code
        == 422
    )


def test_inactive_exercise_keeps_its_name_in_history(client, member, admin):
    record = client.post("/sesiones", headers=member, json=session_payload()).json()["registros"][0]
    name = record["ejercicio_nombre"]
    assert name
    assert (
        client.patch("/admin/ejercicios/1", headers=admin, json={"activo": False}).status_code
        == 200
    )
    assert (
        client.get("/sesiones", headers=member).json()[0]["registros"][0]["ejercicio_nombre"]
        == name
    )
    assert client.post("/sesiones", headers=member, json=session_payload()).status_code == 422


def test_old_history_does_not_get_a_current_forecast(client, member):
    for i in range(4):
        client.post(
            "/sesiones",
            headers=member,
            json=session_payload(30 + i * 2, business_today() - timedelta(weeks=10 - i)),
        )
    result = client.post(
        "/analisis", headers=member, json={"ejercicio_id": 1, "repeticiones": 8}
    ).json()
    assert result["estado"] == "no_estimable" and result["proyeccion"] == []


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


def test_admin_provisioning_is_idempotent_and_preserves_existing_accounts(client, member):
    import pytest

    from app.cli import create_admin
    from app.core.security import verify_password
    from app.modules.users.schemas import Registration

    data = Registration(
        nombre="Provisioned Admin", correo="provisioned@example.com", clave="testing-admin-123"
    )
    with SessionFactory.begin() as db:
        first = create_admin(db, data)
        first_id, first_hash = first.id, first.clave_hash
        again = create_admin(db, data.model_copy(update={"clave": "another-password-123"}))
        assert again.id == first_id and again.clave_hash == first_hash
        assert verify_password(data.clave, first_hash)
        with pytest.raises(ValueError):
            create_admin(db, data.model_copy(update={"correo": "alex@example.com"}))
    token = client.post("/auth/login", json={"correo": data.correo, "clave": data.clave}).json()[
        "access_token"
    ]
    assert (
        client.get("/admin/resumen", headers={"Authorization": f"Bearer {token}"}).status_code
        == 200
    )


def test_overview_reuses_history_and_preserves_achieved_goals(client, member):
    from sqlalchemy import event

    from app.core.database import engine

    client.post(
        "/sesiones", headers=member, json=session_payload(50, business_today() - timedelta(days=1))
    )
    client.post("/sesiones", headers=member, json=session_payload(40))
    for target in [45, 60]:
        assert (
            client.post(
                "/metas", headers=member, json={"ejercicio_id": 1, "carga_objetivo_kg": target}
            ).status_code
            == 201
        )
    queries = []

    def record_query(connection, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", record_query)
    try:
        response = client.get("/inicio", headers=member)
    finally:
        event.remove(engine, "before_cursor_execute", record_query)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["progreso"]["total_sesiones"] == 2
    assert [g["estado"] for g in data["metas"]] == ["alcanzada", "pendiente"]
    assert data["metas"][0]["ultima_carga_kg"] == 40
    assert data["metas"][0]["avance_porcentaje"] == 88.89
    assert sum("FROM gym_app.sesiones" in q for q in queries) == 1
    assert sum("FROM gym_app.registros" in q for q in queries) == 1


def test_analysis_availability_counts_comparable_weeks_and_respects_owner(client, member, admin):
    url = "/analisis/disponibilidad?ejercicio_id=1"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=admin).status_code == 403
    assert client.get("/analisis/disponibilidad?ejercicio_id=0", headers=member).status_code == 422
    assert (
        client.get("/analisis/disponibilidad?ejercicio_id=999", headers=member).status_code == 404
    )
    assert client.get(url, headers=member).json()["grupos"] == []
    for weeks, repetitions in [(3, 10), (3, 10), (2, 10), (1, 10), (0, 10), (0, 8)]:
        payload = session_payload(40, business_today() - timedelta(weeks=weeks))
        payload["registros"][0]["repeticiones"] = repetitions
        assert client.post("/sesiones", headers=member, json=payload).status_code == 201
    response = client.get(url, headers=member)
    assert response.status_code == 200
    groups = response.json()["grupos"]
    assert [(g["repeticiones"], g["semanas"], g["registros"]) for g in groups] == [
        (10, 4, 5),
        (8, 1, 1),
    ]
    assert groups[0]["ultima_fecha"] == business_today().isoformat()
    client.post(
        "/auth/register",
        json={
            "nombre": "Otra Cuenta",
            "correo": "other-readiness@example.com",
            "clave": "password-testing-123",
        },
    )
    token = client.post(
        "/auth/login",
        json={"correo": "other-readiness@example.com", "clave": "password-testing-123"},
    ).json()["access_token"]
    assert client.get(url, headers={"Authorization": f"Bearer {token}"}).json()["grupos"] == []
    # Consultar disponibilidad no guarda análisis ni altera el último resultado.
    assert client.get("/inicio", headers=member).json()["ultimo_analisis"] is None

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.domain import MedicionCorporal, RegistroEjercicio, SesionEntrenamiento
from app.ml.predictor import PredictorCarga, PredictorLineal
from app.ml.preprocessing import comparable_loads, weekly_loads
from app.modules.predictions.schemas import AnalysisInput, Prediction
from app.modules.predictions.service import PredictionService
from app.modules.records.schemas import SessionInput
from app.modules.users.schemas import AccountUpdate, Registration


def test_objects_calculate_volume_and_bmi():
    row = RegistroEjercicio(3, 8, Decimal(32))
    assert row.volumen() == 768
    assert SesionEntrenamiento((row, row)).volumen() == 1536
    assert MedicionCorporal(Decimal(80), Decimal("1.75")).imc() == Decimal("26.12")


@pytest.mark.parametrize("load", [-1, 601, 12.34, True, "20"])
def test_load_filters(load):
    with pytest.raises(ValidationError):
        SessionInput(
            fecha="2026-01-01",
            registros=[{"ejercicio_id": 1, "series": 3, "repeticiones": 8, "carga_kg": load}],
        )


@pytest.mark.parametrize("value", [0, 21, 2.5, True, "3"])
def test_integer_sets(value):
    with pytest.raises(ValidationError):
        SessionInput(
            fecha="2026-01-01",
            registros=[{"ejercicio_id": 1, "series": value, "repeticiones": 8, "carga_kg": 20}],
        )


@pytest.mark.parametrize(
    "value", ["2999-01-01", "2026-02-31", "1999-01-01", "2026-01-01T00:00:00Z"]
)
def test_invalid_dates(value):
    with pytest.raises(ValidationError):
        SessionInput(
            fecha=value,
            registros=[{"ejercicio_id": 1, "series": 3, "repeticiones": 8, "carga_kg": 20}],
        )


def test_public_registration_rejects_role_and_names():
    with pytest.raises(ValidationError):
        Registration(nombre="Max", correo="max@example.com", clave="password-123", rol="admin")
    with pytest.raises(ValidationError):
        Registration(nombre="Max123", correo="max@example.com", clave="password-123")
    assert (
        Registration(nombre="María O’Connor", correo="MAX@example.com", clave="password-123").correo
        == "max@example.com"
    )


def test_partial_profile_rejected():
    with pytest.raises(ValidationError):
        AccountUpdate(edad=24)
    with pytest.raises(ValidationError):
        AccountUpdate(nombre=None)
    assert AccountUpdate(nombre="Max Admin").nombre == "Max Admin"


def test_weekly_preprocessing_preserves_gaps_and_maximum():
    points = weekly_loads(
        [
            (date(2026, 1, 1), Decimal(30)),
            (date(2026, 1, 2), Decimal(32)),
            (date(2026, 1, 22), Decimal(40)),
        ]
    )
    assert points == [{"semana": 0, "carga_kg": 32.0}, {"semana": 3, "carga_kg": 40.0}]


def test_prediction_known_example_and_no_goal():
    points = [{"semana": i, "carga_kg": 32 + i * 2} for i in range(8)]
    result = PredictorLineal().predecir(points, 50)
    assert result.siguiente_carga_kg == 48
    assert result.semanas_hasta_meta == 2
    assert result.pendiente_kg_semana == 2
    assert result.error_mae_kg == 0
    assert result.error_referencia_kg == 2
    assert result.validaciones_temporales == 6
    assert PredictorLineal().predecir(points).semanas_hasta_meta is None


def test_repetition_groups_do_not_mix_heavier_low_rep_records():
    rows = [(date(2026, 1, 1 + i * 7), Decimal(30 + i * 2), 8) for i in range(4)]
    rows.append((date(2026, 1, 22), Decimal(100), 3))
    history, reps = comparable_loads(rows, 8)
    assert reps == 8 and [p["carga_kg"] for p in history] == [30, 32, 34, 36]
    assert comparable_loads(rows)[1] == 8
    assert comparable_loads(rows, 10) == ([], 10)


@pytest.mark.parametrize(
    "loads, weeks, target",
    [
        ([40, 40.1, 40, 40.1], [0, 1, 2, 3], 100),
        ([550, 560, 570, 580], [0, 1, 2, 3], None),
        ([30, 32, 34, 36], [0, 1, 2, 3], 100),
        ([30, 40, 30, 40], [0, 1, 2, 3], None),
        ([30, 32, 34, 36], [0, 1, 10, 11], None),
    ],
)
def test_unreliable_results_never_publish_a_curve_or_eta(loads, weeks, target):
    result = PredictorLineal().predecir(
        [{"semana": week, "carga_kg": load} for week, load in zip(weeks, loads, strict=True)],
        target,
    )
    assert result.estado == "no_estimable"
    assert result.proyeccion == []
    assert result.siguiente_carga_kg is None and result.semanas_hasta_meta is None


def test_temporal_error_uses_only_the_past():
    result = PredictorLineal().predecir(
        [{"semana": i, "carga_kg": load} for i, load in enumerate([30, 32, 34, 60])]
    )
    # Tercera semana: 34 (error 0); cuarta: 36 (error 24). El último punto no entra en su propio ajuste.
    assert result.error_mae_kg == 12
    assert result.error_referencia_kg == 14
    assert result.validaciones_temporales == 2 and result.estado == "no_estimable"


def test_old_analysis_json_still_loads_without_claiming_a_new_model_version():
    old = Prediction(estado="historial_insuficiente", mensaje="Anterior", semanas_observadas=0)
    assert old.modelo_version is None and old.repeticiones_analizadas is None


@pytest.mark.parametrize(
    "loads,target,state",
    [
        ([30], None, "historial_insuficiente"),
        ([30], 20, "meta_alcanzada"),
        ([30, 30, 30, 30], 40, "sin_tendencia_positiva"),
        ([40, 38, 36, 34], 50, "sin_tendencia_positiva"),
    ],
)
def test_prediction_states(loads, target, state):
    result = PredictorLineal().predecir(
        [{"semana": i, "carga_kg": v} for i, v in enumerate(loads)], target
    )
    assert result.estado == state
    assert not result.proyeccion
    assert result.semanas_hasta_meta is None


def test_service_uses_a_substitute_predictor_without_training():
    class FakePredictor(PredictorCarga):
        def predecir(self, historial, meta=None):
            return Prediction(
                estado="historial_insuficiente", mensaje="Prueba", semanas_observadas=len(historial)
            )

    class Repository:
        saved = False

        def exercise(self, value):
            return object()

        def rows(self, user_id, exercise_id):
            return []

        def save(self, user_id, data, result):
            self.saved = True

    class User:
        id = 1
        rol = "usuario"

    repo = Repository()
    assert (
        PredictionService(repo, FakePredictor())
        .analyze(User(), AnalysisInput(ejercicio_id=1))
        .mensaje
        == "Prueba"
    )
    assert repo.saved


@pytest.mark.parametrize(
    "email",
    [
        "sin-arroba",
        "@example.com",
        "max@",
        "max@@example.com",
        "max example@example.com",
        "max@example",
        "max@example..com",
    ],
)
def test_email_format_is_rejected_everywhere(email):
    from app.modules.admin.schemas import AdminCreate, AdminUpdate
    from app.modules.users.schemas import Credentials

    for schema, extra in [
        (Registration, {"nombre": "Max Admin", "clave": "password-123"}),
        (AdminCreate, {"nombre": "Max Admin", "clave": "password-123"}),
        (Credentials, {"clave": "password-123"}),
        (AccountUpdate, {}),
        (AdminUpdate, {}),
    ]:
        with pytest.raises(ValidationError):
            schema(correo=email, **extra)


def test_email_is_normalized_without_dns_verification(monkeypatch):
    import dns.resolver

    from app.modules.admin.schemas import AdminUpdate

    def no_network(*args, **kwargs):
        raise AssertionError("El formato del correo no requiere consultar DNS.")

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", no_network)
    email = "MAX@direccion-inventada-del-gimnasio-987654.com"
    assert (
        Registration(nombre="Max Admin", correo=email, clave="password-123").correo == email.lower()
    )
    assert AccountUpdate(correo=email).correo == email.lower()
    assert AdminUpdate(correo=email).correo == email.lower()


def test_admin_environment_validates_and_hides_the_password(monkeypatch):
    from app.core.bootstrap import AdminSettings

    monkeypatch.setenv("ADMIN_NOMBRE", "Max Admin")
    monkeypatch.setenv("ADMIN_CORREO", "ADMIN@example.com")
    monkeypatch.setenv("ADMIN_CLAVE", "testing-admin-123")
    settings = AdminSettings(_env_file=None)
    assert "testing-admin-123" not in repr(settings)
    assert settings.registration().correo == "admin@example.com"
    monkeypatch.setenv("ADMIN_CLAVE", "short")
    with pytest.raises(ValidationError):
        AdminSettings(_env_file=None).registration()


def test_database_diagnostics_do_not_log_credentials(caplog):
    from sqlalchemy.exc import OperationalError

    from app.core.diagnostics import report_database_error

    class Original(Exception):
        sqlstate = "28P01"

    error = OperationalError(
        "query",
        {"secret": "private-value"},
        Original("password authentication failed postgresql://user:private-value@host"),
    )
    report_database_error(error)
    assert "autenticacion_rechazada" in caplog.text
    assert "28P01" in caplog.text
    assert "private-value" not in caplog.text
    assert "postgresql://" not in caplog.text

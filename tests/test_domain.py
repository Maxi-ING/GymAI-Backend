from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.domain import MedicionCorporal, RegistroEjercicio, SesionEntrenamiento
from app.ml.predictor import PredictorCarga, PredictorLineal
from app.ml.preprocessing import weekly_loads
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
    assert PredictorLineal().predecir(points).semanas_hasta_meta is None


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

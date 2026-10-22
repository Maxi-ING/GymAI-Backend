from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from app.core.validation import Input, Output, PositiveId, Target

Repetitions = Annotated[int, Field(strict=True, ge=1, le=100)]


class GoalInput(Input):
    ejercicio_id: PositiveId
    carga_objetivo_kg: Target
    repeticiones_objetivo: Repetitions | None = None


class GoalOut(Output):
    id: int
    ejercicio_id: int
    carga_objetivo_kg: float
    estado: Literal["pendiente", "alcanzada"]
    repeticiones_objetivo: int | None = None


class AnalysisInput(Input):
    ejercicio_id: PositiveId
    meta_id: PositiveId | None = None
    repeticiones: Repetitions | None = None


class ComparableGroup(Output):
    repeticiones: int
    registros: int
    semanas: int
    ultima_fecha: date


class AnalysisAvailability(Output):
    ejercicio_id: int
    minimo_semanas: int = 4
    grupos: list[ComparableGroup]


class PredictionPoint(Output):
    semana: int
    carga_kg: float


class Prediction(Output):
    estado: Literal[
        "estimado",
        "historial_insuficiente",
        "meta_alcanzada",
        "sin_tendencia_positiva",
        "no_estimable",
    ]
    mensaje: str
    semanas_observadas: int
    pendiente_kg_semana: float | None = None
    siguiente_carga_kg: float | None = None
    semanas_hasta_meta: float | None = None
    historial: list[PredictionPoint] = []
    proyeccion: list[PredictionPoint] = []
    modelo_version: str | None = None
    repeticiones_analizadas: int | None = None
    error_mae_kg: float | None = None
    error_referencia_kg: float | None = None
    validaciones_temporales: int = 0

from typing import Literal

from app.core.validation import Input, Output, PositiveId, Target


class GoalInput(Input):
    ejercicio_id: PositiveId
    carga_objetivo_kg: Target


class GoalOut(Output):
    id: int
    ejercicio_id: int
    carga_objetivo_kg: float
    estado: Literal["pendiente", "alcanzada"]


class AnalysisInput(Input):
    ejercicio_id: PositiveId
    meta_id: PositiveId | None = None


class PredictionPoint(Output):
    semana: int
    carga_kg: float


class Prediction(Output):
    estado: Literal[
        "estimado", "historial_insuficiente", "meta_alcanzada", "sin_tendencia_positiva"
    ]
    mensaje: str
    semanas_observadas: int
    pendiente_kg_semana: float | None = None
    siguiente_carga_kg: float | None = None
    semanas_hasta_meta: float | None = None
    historial: list[PredictionPoint] = []
    proyeccion: list[PredictionPoint] = []

from datetime import date, datetime
from typing import Literal

from app.core.validation import Output
from app.modules.predictions.schemas import GoalOut, Prediction
from app.modules.users.schemas import MeasurementOut


class ProgressPoint(Output):
    fecha: date
    carga_kg: float
    volumen_kg: float


class Progress(Output):
    total_sesiones: int
    volumen_total_kg: float
    carga_maxima_kg: float | None
    ultima_medicion: MeasurementOut | None
    puntos: list[ProgressPoint]


class Performance(Output):
    ejercicio_id: int
    nombre: str
    sesiones: int
    primera_carga_kg: float | None
    ultima_carga_kg: float | None
    mejor_carga_kg: float | None
    variacion_porcentaje: float | None


class OverviewGoal(GoalOut):
    ejercicio_nombre: str
    ultima_carga_kg: float | None
    avance_porcentaje: float | None


class LastAnalysis(Output):
    ejercicio_nombre: str
    fecha: datetime
    resultado: Prediction


class Recommendation(Output):
    titulo: str
    mensaje: str
    origen: Literal["regla", "modelo"]
    accion: Literal["registro", "perfil", "analisis"]


class Overview(Output):
    progreso: Progress
    rendimiento: list[Performance]
    metas: list[OverviewGoal]
    ultimo_analisis: LastAnalysis | None
    recomendaciones: list[Recommendation]

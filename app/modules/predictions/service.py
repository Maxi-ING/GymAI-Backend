from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.core.contracts import GoalData
from app.core.validation import business_today
from app.ml.predictor import PredictorCarga
from app.ml.preprocessing import comparable_loads
from app.modules.predictions.models import Meta
from app.modules.predictions.repository import PredictionRepository
from app.modules.predictions.schemas import AnalysisInput, GoalInput, Prediction
from app.modules.users.models import Usuario


def goal_summary(item: Meta, maximum: Decimal | None) -> GoalData:
    """Deriva el estado de una meta desde la máxima carga comparable."""
    return {
        "id": item.id,
        "ejercicio_id": item.ejercicio_id,
        "carga_objetivo_kg": float(item.carga_objetivo_kg),
        "repeticiones_objetivo": item.repeticiones_objetivo,
        "estado": "alcanzada"
        if maximum is not None and maximum >= item.carga_objetivo_kg
        else "pendiente",
    }


class PredictionService:
    """Coordina las metas y el análisis bajo solicitud del usuario."""

    def __init__(self, repository: PredictionRepository, predictor: PredictorCarga) -> None:
        """Recibe persistencia y contrato predictivo como colaboradores sustituibles."""
        self.repository = repository
        self.predictor = predictor

    def goal_result(self, item: Meta) -> GoalData:
        """Compara la meta con su historial y respeta las repeticiones objetivo."""
        rows = self.repository.rows(item.usuario_id, item.ejercicio_id)
        return goal_summary(
            item,
            max(
                (
                    r.carga_kg
                    for r in rows
                    if item.repeticiones_objetivo is None
                    or r.repeticiones == item.repeticiones_objetivo
                ),
                default=None,
            ),
        )

    def goals(self, user_id: int) -> list[GoalData]:
        """Resume las metas usando máximos agrupados para evitar consultas por cada meta."""
        items = self.repository.goals(user_id)
        maxima = self.repository.maxima(user_id) if items else []
        return [
            goal_summary(
                item,
                max(
                    (
                        load
                        for exercise, reps, load in maxima
                        if exercise == item.ejercicio_id
                        and (
                            item.repeticiones_objetivo is None or reps == item.repeticiones_objetivo
                        )
                    ),
                    default=None,
                ),
            )
            for item in items
        ]

    def create_goal(self, user: Usuario, data: GoalInput) -> GoalData:
        """Valida el ejercicio activo, guarda la meta y devuelve su estado actual."""
        if not self.repository.exercise(data.ejercicio_id, active=True):
            raise HTTPException(422, "El ejercicio no existe o está inactivo.")
        return self.goal_result(self.repository.add_goal(user.id, data))

    def analyze(self, user: Usuario, data: AnalysisInput) -> Prediction:
        """Valida permisos y grupo comparable; predice, comprueba actualidad y guarda el resultado."""
        if user.rol == "admin":
            raise HTTPException(403, "La administración no ejecuta el modelo.")
        if not self.repository.exercise(data.ejercicio_id):
            raise HTTPException(404, "Ejercicio no disponible.")
        goal = None
        if data.meta_id is not None:
            goal = self.repository.goal(user.id, data.meta_id, data.ejercicio_id)
            if goal is None:
                raise HTTPException(404, "Meta no disponible para este ejercicio y cuenta.")
        repetitions = data.repeticiones
        if goal is not None and goal.repeticiones_objetivo is not None:
            if repetitions is not None and repetitions != goal.repeticiones_objetivo:
                raise HTTPException(
                    422, "Las repeticiones del análisis deben coincidir con las de la meta."
                )
            repetitions = goal.repeticiones_objetivo
        rows = self.repository.rows(user.id, data.ejercicio_id)
        history, repetitions = comparable_loads(rows, repetitions)
        result = self.predictor.predecir(history, float(goal.carga_objetivo_kg) if goal else None)
        result = result.model_copy(update={"repeticiones_analizadas": repetitions})
        if result.estado == "estimado" and max(
            row.fecha for row in rows if row.repeticiones == repetitions
        ) < business_today() - timedelta(days=28):
            result = result.model_copy(
                update={
                    "estado": "no_estimable",
                    "mensaje": "No estimable con suficiente fiabilidad: el último registro comparable tiene más de cuatro semanas. Añade sesiones recientes.",
                    "siguiente_carga_kg": None,
                    "semanas_hasta_meta": None,
                    "proyeccion": [],
                }
            )
        self.repository.save(user.id, data, result)
        return result

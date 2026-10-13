from fastapi import HTTPException

from app.ml.predictor import PredictorCarga
from app.ml.preprocessing import weekly_loads
from app.modules.predictions.repository import PredictionRepository


def goal_summary(item, maximum):
    return {
        "id": item.id,
        "ejercicio_id": item.ejercicio_id,
        "carga_objetivo_kg": float(item.carga_objetivo_kg),
        "estado": "alcanzada"
        if maximum is not None and maximum >= item.carga_objetivo_kg
        else "pendiente",
    }


class PredictionService:
    def __init__(self, repository: PredictionRepository, predictor: PredictorCarga):
        self.repository = repository
        self.predictor = predictor

    def goal_result(self, item):
        rows = self.repository.rows(item.usuario_id, item.ejercicio_id)
        return goal_summary(item, max((r.carga_kg for r in rows), default=None))

    def create_goal(self, user, data):
        if not self.repository.exercise(data.ejercicio_id, active=True):
            raise HTTPException(422, "El ejercicio no existe o está inactivo.")
        return self.goal_result(self.repository.add_goal(user.id, data))

    def analyze(self, user, data):
        if user.rol == "admin":
            raise HTTPException(403, "La administración no ejecuta el modelo.")
        if not self.repository.exercise(data.ejercicio_id):
            raise HTTPException(404, "Ejercicio no disponible.")
        goal = None
        if data.meta_id is not None:
            goal = self.repository.goal(user.id, data.meta_id, data.ejercicio_id)
            if goal is None:
                raise HTTPException(404, "Meta no disponible para este ejercicio y cuenta.")
        history = weekly_loads(self.repository.rows(user.id, data.ejercicio_id))
        result = self.predictor.predecir(history, float(goal.carga_objetivo_kg) if goal else None)
        self.repository.save(user.id, data, result)
        return result

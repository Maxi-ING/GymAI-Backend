from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import DB, CurrentUser
from app.ml.predictor import PredictorLineal
from app.modules.predictions.repository import PredictionRepository
from app.modules.predictions.schemas import (
    AnalysisAvailability,
    AnalysisInput,
    GoalInput,
    GoalOut,
    Prediction,
)
from app.modules.predictions.service import PredictionService

router = APIRouter(tags=["Metas y análisis"])


def service(db):
    return PredictionService(PredictionRepository(db), PredictorLineal())


@router.get("/metas", response_model=list[GoalOut])
def goals(db: DB, user: CurrentUser):
    svc = service(db)
    return svc.goals(user.id)


@router.post("/metas", response_model=GoalOut, status_code=201)
def create_goal(data: GoalInput, db: DB, user: CurrentUser):
    return service(db).create_goal(user, data)


@router.post("/analisis", response_model=Prediction)
def analyze(data: AnalysisInput, db: DB, user: CurrentUser):
    return service(db).analyze(user, data)


@router.get("/analisis/disponibilidad", response_model=AnalysisAvailability)
def availability(ejercicio_id: Annotated[int, Query(gt=0)], db: DB, user: CurrentUser):
    return service(db).availability(user, ejercicio_id)

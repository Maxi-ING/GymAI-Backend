from fastapi import APIRouter

from app.core.dependencies import DB, CurrentUser
from app.ml.predictor import PredictorLineal
from app.modules.predictions.repository import PredictionRepository
from app.modules.predictions.schemas import AnalysisInput, GoalInput, GoalOut, Prediction
from app.modules.predictions.service import PredictionService

router = APIRouter(tags=["Metas y análisis"])


def service(db):
    return PredictionService(PredictionRepository(db), PredictorLineal())


@router.get("/metas", response_model=list[GoalOut])
def goals(db: DB, user: CurrentUser):
    svc = service(db)
    return [svc.goal_result(item) for item in svc.repository.goals(user.id)]


@router.post("/metas", response_model=GoalOut, status_code=201)
def create_goal(data: GoalInput, db: DB, user: CurrentUser):
    return service(db).create_goal(user, data)


@router.post("/analisis", response_model=Prediction)
def analyze(data: AnalysisInput, db: DB, user: CurrentUser):
    return service(db).analyze(user, data)

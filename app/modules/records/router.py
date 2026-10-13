from fastapi import APIRouter

from app.core.dependencies import DB, CurrentUser
from app.modules.records.repository import RecordRepository
from app.modules.records.schemas import ExerciseOut, SessionInput, SessionOut
from app.modules.records.service import RecordService

router = APIRouter(tags=["Entrenamiento"])


@router.get("/ejercicios", response_model=list[ExerciseOut])
def exercises(db: DB, user: CurrentUser):
    return RecordRepository(db).exercises()


@router.get("/sesiones", response_model=list[SessionOut])
def sessions(db: DB, user: CurrentUser):
    return list(reversed(RecordRepository(db).sessions(user.id)))


@router.post("/sesiones", response_model=SessionOut, status_code=201)
def create(data: SessionInput, db: DB, user: CurrentUser):
    return RecordService(RecordRepository(db)).create(user, data)

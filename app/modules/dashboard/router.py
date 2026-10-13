from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import DB, CurrentUser
from app.core.validation import BusinessDate
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import Overview, Progress
from app.modules.dashboard.service import DashboardService

router = APIRouter(tags=["Inicio y progreso"])


@router.get("/progreso", response_model=Progress)
def progress(
    db: DB,
    user: CurrentUser,
    ejercicio_id: Annotated[int | None, Query(gt=0)] = None,
    desde: BusinessDate | None = None,
    hasta: BusinessDate | None = None,
):
    return DashboardService(DashboardRepository(db)).progress(user.id, ejercicio_id, desde, hasta)


@router.get("/inicio", response_model=Overview)
def overview(db: DB, user: CurrentUser):
    return DashboardService(DashboardRepository(db)).overview(user)

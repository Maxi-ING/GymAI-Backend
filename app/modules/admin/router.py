from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Response

from app.core.dependencies import DB, AdminUser
from app.modules.admin.repository import AdminRepository
from app.modules.admin.schemas import (
    AdminCreate,
    AdminDetail,
    AdminSummary,
    AdminUpdate,
    ExerciseCreate,
    ExerciseUpdate,
    SessionPage,
    UserPage,
)
from app.modules.admin.service import AdminService
from app.modules.records.repository import RecordRepository
from app.modules.records.schemas import ExerciseOut
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/admin", tags=["Administración"])
Id = Annotated[int, Path(gt=0)]


@router.get("/resumen", response_model=AdminSummary)
def summary(db: DB, actor: AdminUser):
    return AdminService(AdminRepository(db)).summary()


@router.get("/usuarios", response_model=UserPage)
def users(
    db: DB,
    actor: AdminUser,
    q: Annotated[str, Query(max_length=100)] = "",
    rol: Literal["admin", "usuario"] | None = None,
    estado: Literal["activo", "inactivo"] | None = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
):
    return AdminRepository(db).users(q.strip(), rol, estado, pagina)


@router.post("/usuarios", response_model=UserOut, status_code=201)
def create_user(data: AdminCreate, db: DB, actor: AdminUser):
    return AdminService(AdminRepository(db)).create_user(actor, data)


@router.get("/usuarios/{user_id}", response_model=AdminDetail)
def detail(user_id: Id, db: DB, actor: AdminUser):
    return AdminService(AdminRepository(db)).detail(user_id)


@router.patch("/usuarios/{user_id}", response_model=UserOut)
def update_user(user_id: Id, data: AdminUpdate, db: DB, actor: AdminUser):
    return AdminService(AdminRepository(db)).update_user(actor, user_id, data)


@router.get("/sesiones", response_model=SessionPage)
def sessions(
    db: DB,
    actor: AdminUser,
    usuario_id: Annotated[int | None, Query(gt=0)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
):
    return AdminRepository(db).sessions(usuario_id, pagina)


@router.delete("/sesiones/{session_id}", status_code=204)
def delete_session(session_id: Id, db: DB, actor: AdminUser):
    AdminService(AdminRepository(db)).delete_session(actor, session_id)
    return Response(status_code=204)


@router.delete("/metas/{goal_id}", status_code=204)
def delete_goal(goal_id: Id, db: DB, actor: AdminUser):
    AdminService(AdminRepository(db)).delete_goal(actor, goal_id)
    return Response(status_code=204)


@router.get("/ejercicios", response_model=list[ExerciseOut])
def exercises(db: DB, actor: AdminUser):
    return RecordRepository(db).exercises(active_only=False)


@router.post("/ejercicios", response_model=ExerciseOut, status_code=201)
def create_exercise(data: ExerciseCreate, db: DB, actor: AdminUser):
    return AdminService(AdminRepository(db)).create_exercise(actor, data)


@router.patch("/ejercicios/{exercise_id}", response_model=ExerciseOut)
def update_exercise(exercise_id: Id, data: ExerciseUpdate, db: DB, actor: AdminUser):
    return AdminService(AdminRepository(db)).update_exercise(actor, exercise_id, data)

from fastapi import HTTPException
from sqlalchemy import select

from app.core.security import hash_password
from app.ml.predictor import PredictorLineal
from app.modules.admin.repository import AdminRepository
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.service import DashboardService
from app.modules.predictions.models import Meta
from app.modules.predictions.repository import PredictionRepository
from app.modules.predictions.service import PredictionService
from app.modules.records.models import Ejercicio, Sesion
from app.modules.users.models import Usuario
from app.modules.users.repository import UserRepository


class AdminService:
    def __init__(self, repository: AdminRepository):
        self.repository = repository
        self.db = repository.db

    def summary(self):
        repo = self.repository
        return {
            "total_usuarios": repo.count(Usuario),
            "usuarios_activos": repo.count(Usuario, Usuario.activo.is_(True)),
            "total_sesiones": repo.count(Sesion),
            "total_ejercicios": repo.count(Ejercicio, Ejercicio.activo.is_(True)),
            "sesiones_recientes": repo.sessions(limit=5)["items"],
        }

    def detail(self, user_id):
        user = self.repository.user(user_id)
        if user is None:
            raise HTTPException(404, "Usuario no disponible.")
        goals = PredictionService(PredictionRepository(self.db), PredictorLineal())
        return {
            "usuario": user,
            "progreso": DashboardService(DashboardRepository(self.db)).progress(user_id),
            "sesiones": self.repository.sessions(user_id)["items"],
            "metas": goals.goals(user_id),
        }

    def create_user(self, actor, data):
        self.repository.lock_roles()
        users = UserRepository(self.db)
        if users.by_email(data.correo):
            raise HTTPException(409, "El correo ya está registrado.")
        user = users.create(
            nombre=data.nombre,
            correo=data.correo,
            clave_hash=hash_password(data.clave),
            rol=data.rol,
        )
        self.repository.audit(actor, "crear_usuario", "usuario", user.id, {"rol": data.rol})
        return user

    def update_user(self, actor, user_id, data):
        self.repository.lock_roles()
        user = self.repository.user(user_id, locked=True)
        if user is None:
            raise HTTPException(404, "Usuario no disponible.")
        values = data.model_dump(exclude_unset=True)
        removing = values.get("rol", user.rol) != "admin" or not values.get("activo", user.activo)
        if user.id == actor.id and removing:
            raise HTTPException(409, "No puedes desactivar tu cuenta ni retirar tu propio rol.")
        if (
            user.rol == "admin"
            and user.activo
            and removing
            and self.repository.active_admins() <= 1
        ):
            raise HTTPException(409, "Debe conservarse al menos un administrador activo.")
        for field, value in values.items():
            setattr(user, field, value)
        self.db.flush()
        self.repository.audit(actor, "actualizar_usuario", "usuario", user.id, values)
        return user

    def delete_session(self, actor, session_id):
        item = self.db.scalar(select(Sesion).where(Sesion.id == session_id).with_for_update())
        if item is None:
            raise HTTPException(404, "Sesión no disponible.")
        detail = {
            "usuario_id": item.usuario_id,
            "fecha": item.fecha.isoformat(),
            "registros": len(item.registros),
        }
        self.db.delete(item)
        self.repository.audit(actor, "eliminar_sesion", "sesion", session_id, detail)

    def delete_goal(self, actor, goal_id):
        item = self.db.get(Meta, goal_id)
        if item is None:
            raise HTTPException(404, "Meta no disponible.")
        self.db.delete(item)
        self.repository.audit(actor, "eliminar_meta", "meta", goal_id)

    def create_exercise(self, actor, data):
        item = Ejercicio(
            nombre=data.nombre, nombre_normalizado=data.nombre.casefold(), unidad=data.unidad
        )
        self.db.add(item)
        self.db.flush()
        self.repository.audit(actor, "crear_ejercicio", "ejercicio", item.id)
        return item

    def update_exercise(self, actor, exercise_id, data):
        item = self.db.scalar(
            select(Ejercicio).where(Ejercicio.id == exercise_id).with_for_update()
        )
        if item is None:
            raise HTTPException(404, "Ejercicio no disponible.")
        values = data.model_dump(exclude_unset=True)
        for field, value in values.items():
            setattr(item, field, value)
        if "nombre" in values:
            item.nombre_normalizado = item.nombre.casefold()
        self.db.flush()
        self.repository.audit(actor, "actualizar_ejercicio", "ejercicio", item.id, values)
        return item

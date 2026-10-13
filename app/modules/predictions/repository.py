from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.predictions.models import Analisis, Meta
from app.modules.records.models import Ejercicio, Registro, Sesion


class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def goals(self, user_id):
        return list(
            self.db.scalars(select(Meta).where(Meta.usuario_id == user_id).order_by(Meta.id))
        )

    def goal(self, user_id, goal_id, exercise_id):
        return self.db.scalar(
            select(Meta).where(
                Meta.id == goal_id, Meta.usuario_id == user_id, Meta.ejercicio_id == exercise_id
            )
        )

    def exercise(self, exercise_id, active=False):
        query = select(Ejercicio).where(Ejercicio.id == exercise_id)
        if active:
            query = query.where(Ejercicio.activo.is_(True)).with_for_update(read=True)
        return self.db.scalar(query)

    def rows(self, user_id, exercise_id):
        return list(
            self.db.execute(
                select(Sesion.fecha, Registro.carga_kg)
                .join(Registro, Registro.sesion_id == Sesion.id)
                .where(Sesion.usuario_id == user_id, Registro.ejercicio_id == exercise_id)
                .order_by(Sesion.fecha, Sesion.id)
            )
        )

    def add_goal(self, user_id, data):
        item = Meta(usuario_id=user_id, **data.model_dump())
        self.db.add(item)
        self.db.flush()
        return item

    def save(self, user_id, data, result):
        item = Analisis(
            usuario_id=user_id,
            ejercicio_id=data.ejercicio_id,
            meta_id=data.meta_id,
            resultado=result.model_dump(mode="json"),
        )
        self.db.add(item)
        self.db.flush()
        return item

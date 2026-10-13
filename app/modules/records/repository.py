from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.records.models import Ejercicio, Registro, Sesion


class RecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def exercises(self, active_only=True):
        query = select(Ejercicio).order_by(Ejercicio.id)
        if active_only:
            query = query.where(Ejercicio.activo.is_(True))
        return list(self.db.scalars(query))

    def enabled_exercises(self, ids):
        # SHARE impide desactivar el catálogo mientras se confirma una sesión.
        return list(
            self.db.scalars(
                select(Ejercicio)
                .where(Ejercicio.id.in_(ids), Ejercicio.activo.is_(True))
                .order_by(Ejercicio.id)
                .with_for_update(read=True)
            )
        )

    def sessions(self, user_id, desde=None, hasta=None):
        query = (
            select(Sesion)
            .where(Sesion.usuario_id == user_id)
            .options(selectinload(Sesion.registros))
        )
        if desde:
            query = query.where(Sesion.fecha >= desde)
        if hasta:
            query = query.where(Sesion.fecha <= hasta)
        return list(self.db.scalars(query.order_by(Sesion.fecha, Sesion.id)))

    def create(self, user_id, data):
        item = Sesion(
            usuario_id=user_id,
            fecha=data.fecha,
            registros=[Registro(**row.model_dump()) for row in data.registros],
        )
        self.db.add(item)
        self.db.flush()
        return item

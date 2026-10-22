from __future__ import annotations

from collections.abc import Collection
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.records.models import Ejercicio, Registro, Sesion
from app.modules.records.schemas import SessionInput


class RecordRepository:
    """Gestiona el catálogo y la persistencia de sesiones con sus detalles."""

    def __init__(self, db: Session) -> None:
        """Usa la sesión de base de datos de la solicitud."""
        self.db = db

    def exercises(self, active_only: bool = True) -> list[Ejercicio]:
        """Lista el catálogo ordenado y permite incluir ejercicios desactivados."""
        query = select(Ejercicio).order_by(Ejercicio.id)
        if active_only:
            query = query.where(Ejercicio.activo.is_(True))
        return list(self.db.scalars(query))

    def enabled_exercises(self, ids: Collection[int]) -> list[Ejercicio]:
        """Bloquea en modo compartido los ejercicios activos durante el registro."""
        # SHARE impide desactivar el catálogo mientras se confirma una sesión.
        return list(
            self.db.scalars(
                select(Ejercicio)
                .where(Ejercicio.id.in_(ids), Ejercicio.activo.is_(True))
                .order_by(Ejercicio.id)
                .with_for_update(read=True)
            )
        )

    def sessions(
        self, user_id: int, desde: date | None = None, hasta: date | None = None
    ) -> list[Sesion]:
        """Obtiene sesiones de una cuenta, con sus detalles y filtros de fecha opcionales."""
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

    def create(self, user_id: int, data: SessionInput) -> Sesion:
        """Inserta cabecera y detalles; la confirmación corresponde a get_db()."""
        item = Sesion(
            usuario_id=user_id,
            fecha=data.fecha,
            registros=[Registro(**row.model_dump()) for row in data.registros],
        )
        self.db.add(item)
        self.db.flush()
        return item

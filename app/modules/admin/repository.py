from __future__ import annotations

from typing import Literal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.contracts import AdminSessionData, Page
from app.core.database import Base
from app.modules.admin.models import Auditoria
from app.modules.records.models import Sesion
from app.modules.users.models import Usuario
from app.modules.users.schemas import Role

ADMIN_LOCK = 73519001


class AdminRepository:
    """Consulta datos globales y registra auditoría administrativa."""

    def __init__(self, db: Session) -> None:
        """Comparte la transacción de la operación administrativa."""
        self.db = db

    def lock_roles(self) -> None:
        """Serializa cambios de acceso para conservar al menos un administrador activo."""
        # Todos los cambios de permisos serializan la comprobación del último admin.
        self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADMIN_LOCK})

    def user(self, user_id: int, locked: bool = False) -> Usuario | None:
        """Obtiene una cuenta y permite bloquearla durante una modificación."""
        query = (
            select(Usuario).where(Usuario.id == user_id).execution_options(populate_existing=True)
        )
        if locked:
            query = query.with_for_update()
        return self.db.scalar(query)

    def active_admins(self) -> int:
        """Cuenta los administradores activos de la plataforma."""
        return self.db.scalar(
            select(func.count())
            .select_from(Usuario)
            .where(Usuario.rol == "admin", Usuario.activo.is_(True))
        )

    def users(
        self,
        q: str = "",
        rol: Role | None = None,
        estado: Literal["activo", "inactivo"] | None = None,
        pagina: int = 1,
    ) -> Page[Usuario]:
        """Lista usuarios con filtros parametrizados y paginación de diez elementos."""
        query = select(Usuario)
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(
                Usuario.nombre.ilike(f"%{escaped}%", escape="\\")
                | Usuario.correo.ilike(f"%{escaped}%", escape="\\")
            )
        if rol:
            query = query.where(Usuario.rol == rol)
        if estado:
            query = query.where(Usuario.activo.is_(estado == "activo"))
        total = self.db.scalar(select(func.count()).select_from(query.subquery()))
        items = list(
            self.db.scalars(query.order_by(Usuario.id).offset((pagina - 1) * 10).limit(10))
        )
        return {"items": items, "total": total, "pagina": pagina, "por_pagina": 10}

    def sessions(
        self, user_id: int | None = None, pagina: int = 1, limit: int = 10
    ) -> Page[AdminSessionData]:
        """Lista sesiones con propietario y detalle, globales o de una cuenta."""
        query = (
            select(Sesion, Usuario.nombre)
            .join(Usuario, Usuario.id == Sesion.usuario_id)
            .options(selectinload(Sesion.registros))
        )
        if user_id is not None:
            query = query.where(Sesion.usuario_id == user_id)
        total = self.db.scalar(select(func.count()).select_from(query.subquery()))
        rows = self.db.execute(
            query.order_by(Sesion.fecha.desc(), Sesion.id.desc())
            .offset((pagina - 1) * limit)
            .limit(limit)
        )
        items = [
            {
                "id": s.id,
                "fecha": s.fecha,
                "registros": s.registros,
                "volumen_kg": s.volumen_kg,
                "usuario_id": s.usuario_id,
                "usuario_nombre": name,
            }
            for s, name in rows
        ]
        return {"items": items, "total": total, "pagina": pagina, "por_pagina": limit}

    def count(self, model: type[Base], *conditions: ColumnElement[bool]) -> int:
        """Cuenta filas que satisfacen las condiciones SQLAlchemy recibidas."""
        return self.db.scalar(select(func.count()).select_from(model).where(*conditions))

    def audit(
        self,
        actor: Usuario,
        action: str,
        resource: str,
        resource_id: int,
        detail: dict[str, object] | None = None,
    ) -> None:
        """Registra el cambio administrativo en la misma transacción, sin credenciales."""
        self.db.add(
            Auditoria(
                actor_id=actor.id,
                accion=action,
                recurso=resource,
                recurso_id=resource_id,
                detalle=detail or {},
            )
        )
        self.db.flush()

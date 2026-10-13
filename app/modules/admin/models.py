from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (Index("ix_auditoria_actor_id", "actor_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("gym_app.usuarios.id"))
    accion: Mapped[str] = mapped_column(String(60))
    recurso: Mapped[str] = mapped_column(String(60))
    recurso_id: Mapped[int]
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    detalle: Mapped[dict] = mapped_column(JSONB, default=dict)

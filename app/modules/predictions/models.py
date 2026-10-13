from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.records.models import Ejercicio


class Meta(Base):
    __tablename__ = "metas"
    __table_args__ = (
        CheckConstraint("carga_objetivo_kg > 0 AND carga_objetivo_kg <= 600", name="carga"),
        Index("ix_metas_usuario_ejercicio", "usuario_id", "ejercicio_id"),
        Index("ix_metas_ejercicio_id", "ejercicio_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("gym_app.usuarios.id"))
    ejercicio_id: Mapped[int] = mapped_column(ForeignKey("gym_app.ejercicios.id"))
    carga_objetivo_kg: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    ejercicio: Mapped[Ejercicio] = relationship(lazy="joined")


class Analisis(Base):
    __tablename__ = "analisis"
    __table_args__ = (
        Index("ix_analisis_usuario_fecha", "usuario_id", "fecha"),
        Index("ix_analisis_ejercicio_id", "ejercicio_id"),
        Index("ix_analisis_meta_id", "meta_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("gym_app.usuarios.id"))
    ejercicio_id: Mapped[int] = mapped_column(ForeignKey("gym_app.ejercicios.id"))
    meta_id: Mapped[int | None] = mapped_column(ForeignKey("gym_app.metas.id", ondelete="SET NULL"))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resultado: Mapped[dict] = mapped_column(JSONB)
    ejercicio: Mapped[Ejercicio] = relationship(lazy="joined")

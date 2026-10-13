from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.domain import RegistroEjercicio, SesionEntrenamiento


class Ejercicio(Base):
    __tablename__ = "ejercicios"
    __table_args__ = (CheckConstraint("unidad = 'kg'", name="unidad"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    nombre_normalizado: Mapped[str] = mapped_column(String(80), unique=True)
    unidad: Mapped[str] = mapped_column(String(5), default="kg", server_default="kg")
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Sesion(Base):
    __tablename__ = "sesiones"
    __table_args__ = (
        CheckConstraint("fecha >= DATE '2000-01-01'", name="fecha"),
        Index("ix_sesiones_usuario_fecha", "usuario_id", "fecha"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("gym_app.usuarios.id"))
    fecha: Mapped[date] = mapped_column(Date)
    registros: Mapped[list["Registro"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, lazy="selectin"
    )

    @property
    def volumen_kg(self):
        return float(SesionEntrenamiento(tuple(r.dominio() for r in self.registros)).volumen())


class Registro(Base):
    __tablename__ = "registros"
    __table_args__ = (
        CheckConstraint("series BETWEEN 1 AND 20", name="series"),
        CheckConstraint("repeticiones BETWEEN 1 AND 100", name="repeticiones"),
        CheckConstraint("carga_kg BETWEEN 0 AND 600", name="carga"),
        Index("ix_registros_sesion_ejercicio", "sesion_id", "ejercicio_id"),
        Index("ix_registros_ejercicio_id", "ejercicio_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_id: Mapped[int] = mapped_column(ForeignKey("gym_app.sesiones.id", ondelete="CASCADE"))
    ejercicio_id: Mapped[int] = mapped_column(ForeignKey("gym_app.ejercicios.id"))
    series: Mapped[int]
    repeticiones: Mapped[int]
    carga_kg: Mapped[Decimal] = mapped_column(Numeric(4, 1))

    def dominio(self):
        return RegistroEjercicio(self.series, self.repeticiones, self.carga_kg)

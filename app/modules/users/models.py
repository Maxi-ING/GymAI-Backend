from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.domain import MedicionCorporal


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("rol IN ('admin','usuario')", name="rol"),
        CheckConstraint("edad IS NULL OR edad BETWEEN 18 AND 120", name="edad"),
        CheckConstraint("talla_m IS NULL OR talla_m BETWEEN 0.50 AND 2.50", name="talla"),
        CheckConstraint(
            "NOT perfil_completo OR (edad IS NOT NULL AND talla_m IS NOT NULL AND objetivo IS NOT NULL)",
            name="perfil",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    correo: Mapped[str] = mapped_column(String(254), unique=True)
    clave_hash: Mapped[str] = mapped_column(Text)
    rol: Mapped[str] = mapped_column(String(10), default="usuario", server_default="usuario")
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    edad: Mapped[int | None] = mapped_column(Integer)
    talla_m: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    objetivo: Mapped[str | None] = mapped_column(String(60))
    perfil_completo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Medicion(Base):
    __tablename__ = "mediciones"
    __table_args__ = (
        CheckConstraint("peso_kg BETWEEN 20 AND 400", name="peso"),
        CheckConstraint("talla_m BETWEEN 0.50 AND 2.50", name="talla"),
        CheckConstraint("fecha >= DATE '2000-01-01'", name="fecha"),
        Index("ix_mediciones_usuario_fecha", "usuario_id", "fecha"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("gym_app.usuarios.id"))
    fecha: Mapped[date] = mapped_column(Date)
    peso_kg: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    talla_m: Mapped[Decimal] = mapped_column(Numeric(3, 2))

    @property
    def imc(self):
        # Se conserva la talla de esa medición para no cambiar su IMC histórico.
        return float(MedicionCorporal(self.peso_kg, self.talla_m).imc())

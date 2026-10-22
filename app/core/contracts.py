"""Tipos internos de retorno; Pydantic conserva la validación del contrato HTTP."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, TypedDict

from sqlalchemy.engine import Row

from app.modules.records.models import Registro
from app.modules.users.models import Medicion, Usuario

LoadRow = Row[tuple[date, Decimal, int]]
LoadMaximum = Row[tuple[int, int, Decimal]]


class Page[T](TypedDict):
    items: list[T]
    total: int
    pagina: int
    por_pagina: int


class TokenData(TypedDict):
    access_token: str
    token_type: Literal["bearer"]


class GoalData(TypedDict):
    id: int
    ejercicio_id: int
    carga_objetivo_kg: float
    repeticiones_objetivo: int | None
    estado: Literal["pendiente", "alcanzada"]


class GoalProgress(GoalData):
    ejercicio_nombre: str
    ultima_carga_kg: float | Decimal | None
    avance_porcentaje: float | None


class ProgressPointData(TypedDict):
    fecha: date
    carga_kg: Decimal
    volumen_kg: Decimal


class ProgressData(TypedDict):
    total_sesiones: int
    volumen_total_kg: float
    carga_maxima_kg: float | None
    ultima_medicion: Medicion | None
    puntos: list[ProgressPointData]


class PerformanceData(TypedDict):
    ejercicio_id: int
    nombre: str
    sesiones: int
    primera_carga_kg: float
    ultima_carga_kg: float
    mejor_carga_kg: float
    variacion_porcentaje: float | None


class RecommendationData(TypedDict):
    titulo: str
    mensaje: str
    origen: Literal["regla", "modelo"]
    accion: Literal["registro", "perfil", "analisis"]


class AnalysisSnapshot(TypedDict):
    ejercicio_nombre: str
    fecha: datetime
    resultado: dict[str, object]


class OverviewData(TypedDict):
    progreso: ProgressData
    rendimiento: list[PerformanceData]
    metas: list[GoalProgress]
    ultimo_analisis: AnalysisSnapshot | None
    recomendaciones: list[RecommendationData]


class AdminSessionData(TypedDict):
    id: int
    fecha: date
    registros: list[Registro]
    volumen_kg: float
    usuario_id: int
    usuario_nombre: str


class AdminSummaryData(TypedDict):
    total_usuarios: int
    usuarios_activos: int
    total_sesiones: int
    total_ejercicios: int
    sesiones_recientes: list[AdminSessionData]


class AdminDetailData(TypedDict):
    usuario: Usuario
    progreso: ProgressData
    sesiones: list[AdminSessionData]
    metas: list[GoalData]

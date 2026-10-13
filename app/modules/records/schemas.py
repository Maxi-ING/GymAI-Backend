from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from app.core.validation import BusinessDate, Input, Load, Output, PositiveId


class RecordInput(Input):
    ejercicio_id: PositiveId
    series: Annotated[int, Field(strict=True, ge=1, le=20)]
    repeticiones: Annotated[int, Field(strict=True, ge=1, le=100)]
    carga_kg: Load


class SessionInput(Input):
    fecha: BusinessDate
    registros: Annotated[list[RecordInput], Field(min_length=1, max_length=20)]


class RecordOut(Output):
    ejercicio_id: int
    series: int
    repeticiones: int
    carga_kg: float


class SessionOut(Output):
    id: int
    fecha: date
    registros: list[RecordOut]
    volumen_kg: float


class ExerciseOut(Output):
    id: int
    nombre: str
    unidad: Literal["kg"]
    activo: bool

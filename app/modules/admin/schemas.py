import unicodedata
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, model_validator

from app.core.validation import Input, Name, Output
from app.modules.dashboard.schemas import Progress
from app.modules.predictions.schemas import GoalOut
from app.modules.records.schemas import SessionOut
from app.modules.users.schemas import Email, Registration, Role, UserOut


def exercise_name(value):
    value = " ".join(unicodedata.normalize("NFKC", value).split())
    if not 2 <= len(value) <= 80 or len(value.casefold()) > 80:
        raise ValueError("El nombre de ejercicio requiere 2–80 caracteres.")
    return value


ExerciseName = Annotated[str, AfterValidator(exercise_name)]


class AdminCreate(Registration):
    rol: Role = "usuario"


class AdminUpdate(Input):
    nombre: Name | None = None
    correo: Email | None = None
    rol: Role | None = None
    activo: Annotated[bool, Field(strict=True)] | None = None

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set or any(
            getattr(self, f) is None for f in self.model_fields_set
        ):
            raise ValueError("Envía campos no nulos para actualizar.")
        if self.correo:
            self.correo = str(self.correo).lower()
        return self


class ExerciseCreate(Input):
    nombre: ExerciseName
    unidad: Literal["kg"] = "kg"


class ExerciseUpdate(Input):
    nombre: ExerciseName | None = None
    activo: Annotated[bool, Field(strict=True)] | None = None

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set or any(
            getattr(self, f) is None for f in self.model_fields_set
        ):
            raise ValueError("Envía campos no nulos para actualizar.")
        return self


class AdminSession(SessionOut):
    usuario_id: int
    usuario_nombre: str


class UserPage(Output):
    items: list[UserOut]
    total: int
    pagina: int
    por_pagina: int = 10


class SessionPage(Output):
    items: list[AdminSession]
    total: int
    pagina: int
    por_pagina: int = 10


class AdminDetail(Output):
    usuario: UserOut
    progreso: Progress
    sesiones: list[SessionOut]
    metas: list[GoalOut]


class AdminSummary(Output):
    total_usuarios: int
    usuarios_activos: int
    total_sesiones: int
    total_ejercicios: int
    sesiones_recientes: list[AdminSession]

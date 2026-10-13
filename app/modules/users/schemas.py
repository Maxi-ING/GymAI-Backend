from datetime import date
from typing import Annotated, Literal

from pydantic import EmailStr, Field, field_validator, model_validator

from app.core.validation import BusinessDate, Height, Input, Name, Output, Weight

Role = Literal["admin", "usuario"]
Objective = Literal[
    "Ganar fuerza", "Ganar masa muscular", "Mejorar condición física", "Mantener actividad física"
]
Email = Annotated[EmailStr, Field(max_length=254)]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class Credentials(Input):
    correo: Email
    clave: Annotated[str, Field(min_length=1, max_length=128)]

    @field_validator("correo")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class Registration(Credentials):
    nombre: Name
    clave: Password


class UserOut(Output):
    id: int
    nombre: str
    correo: str
    rol: Role
    activo: bool
    edad: int | None
    talla_m: float | None
    objetivo: str | None
    perfil_completo: bool


class AccountUpdate(Input):
    nombre: Name | None = None
    correo: Email | None = None
    edad: Annotated[int, Field(strict=True, ge=18, le=120)] | None = None
    talla_m: Height | None = None
    peso_kg: Weight | None = None
    objetivo: Objective | None = None

    @model_validator(mode="after")
    def complete_update(self):
        if not self.model_fields_set or any(
            getattr(self, f) is None for f in self.model_fields_set
        ):
            raise ValueError("Envía campos no nulos para actualizar.")
        fields = {"edad", "talla_m", "peso_kg", "objetivo"}
        if self.model_fields_set & fields and not fields <= self.model_fields_set:
            raise ValueError("El perfil requiere edad, talla_m, peso_kg y objetivo juntos.")
        if self.correo:
            self.correo = str(self.correo).lower()
        return self


class MeasurementInput(Input):
    fecha: BusinessDate
    peso_kg: Weight


class MeasurementOut(Output):
    id: int
    fecha: date
    peso_kg: float
    imc: float


class TokenOut(Output):
    access_token: str
    token_type: Literal["bearer"] = "bearer"

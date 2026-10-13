import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, BeforeValidator

def business_today():
    return datetime.now(ZoneInfo("America/Lima")).date()

def valid_date(value: date):
    if not date(2000, 1, 1) <= value <= business_today():
        raise ValueError("La fecha debe estar entre 2000-01-01 y hoy, sin fechas futuras.")
    return value

def date_format(value):
    if isinstance(value, str) and (len(value) != 10 or value[4] != "-" or value[7] != "-"):
        raise ValueError("Usa una fecha YYYY-MM-DD.")
    if not isinstance(value, (date, str)) or isinstance(value, datetime):
        raise ValueError("Usa una fecha YYYY-MM-DD.")
    return value

def numeric(value):
    if isinstance(value, (bool, str)):
        raise ValueError("El campo requiere un número JSON.")
    return value

def person_name(value: str):
    value = " ".join(unicodedata.normalize("NFC", value).split())
    def allowed(c):
        return unicodedata.category(c)[0] in "LM" or c in " .'’-"
    if not 2 <= len(value) <= 100 or not value[0].isalpha() or not all(allowed(c) for c in value):
        raise ValueError("Nombre: 2–100 caracteres, letras, espacios, puntos, apóstrofes o guiones.")
    return value

class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False, allow_inf_nan=False)

class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)

PositiveId = Annotated[int, Field(strict=True, gt=0)]
BusinessDate = Annotated[date, BeforeValidator(date_format), AfterValidator(valid_date)]
Name = Annotated[str, AfterValidator(person_name)]
Load = Annotated[Decimal, BeforeValidator(numeric), Field(ge=0, le=600, decimal_places=1)]
Target = Annotated[Decimal, BeforeValidator(numeric), Field(gt=0, le=600, decimal_places=1)]
Weight = Annotated[Decimal, BeforeValidator(numeric), Field(ge=20, le=400, decimal_places=1)]
Height = Annotated[Decimal, BeforeValidator(numeric), Field(ge=Decimal("0.50"), le=Decimal("2.50"), decimal_places=2)]

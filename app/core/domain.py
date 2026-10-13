from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RegistroEjercicio:
    series: int
    repeticiones: int
    carga_kg: Decimal

    def volumen(self) -> Decimal:
        return self.series * self.repeticiones * self.carga_kg


@dataclass(frozen=True)
class SesionEntrenamiento:
    registros: tuple[RegistroEjercicio, ...]

    def volumen(self) -> Decimal:
        return sum((registro.volumen() for registro in self.registros), Decimal(0))


@dataclass(frozen=True)
class MedicionCorporal:
    peso_kg: Decimal
    talla_m: Decimal

    def imc(self) -> Decimal:
        return (self.peso_kg / self.talla_m**2).quantize(Decimal("0.01"))

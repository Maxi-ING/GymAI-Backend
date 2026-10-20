from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import Medicion, Usuario
from app.modules.users.schemas import Role


class UserRepository:
    """Concentra las consultas e inserciones de usuarios y mediciones."""

    def __init__(self, db: Session) -> None:
        """Usa la sesión transaccional proporcionada por la solicitud."""
        self.db = db

    def by_email(self, email: str) -> Usuario | None:
        """Busca el correo normalizado; devuelve None si la cuenta no existe."""
        return self.db.scalar(select(Usuario).where(Usuario.correo == email.lower()))

    def create(
        self, *, nombre: str, correo: str, clave_hash: str, rol: Role = "usuario"
    ) -> Usuario:
        """Inserta y asigna el ID de la cuenta sin confirmar la transacción."""
        user = Usuario(nombre=nombre, correo=correo, clave_hash=clave_hash, rol=rol)
        self.db.add(user)
        self.db.flush()
        return user

    def measurement(self, user: Usuario, fecha: date, peso: Decimal) -> Medicion:
        """Guarda peso y talla de ese momento sin modificar mediciones anteriores."""
        item = Medicion(usuario_id=user.id, fecha=fecha, peso_kg=peso, talla_m=user.talla_m)
        self.db.add(item)
        self.db.flush()
        return item

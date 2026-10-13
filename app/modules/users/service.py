from fastapi import HTTPException

from app.core.security import dummy_hash, hash_password, issue_token, verify_password
from app.core.validation import business_today
from app.modules.users.repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def register(self, data):
        if self.repository.by_email(data.correo):
            raise HTTPException(409, "El correo ya está registrado.")
        return self.repository.create(
            nombre=data.nombre,
            correo=data.correo,
            clave_hash=hash_password(data.clave),
            rol="usuario",
        )

    def login(self, data):
        user = self.repository.by_email(data.correo)
        valid = verify_password(data.clave, user.clave_hash if user else dummy_hash)
        if not user or not valid or not user.activo:
            raise HTTPException(
                401,
                "Credenciales incorrectas o cuenta no disponible.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"access_token": issue_token(user.id), "token_type": "bearer"}

    def update(self, user, data):
        values = data.model_dump(exclude_unset=True)
        for field in ["nombre", "correo", "edad", "talla_m", "objetivo"]:
            if field in values:
                setattr(user, field, values[field])
        if "peso_kg" in values:
            self.repository.measurement(user, business_today(), values["peso_kg"])
            user.perfil_completo = True
        self.repository.db.flush()
        return user

    def measurement(self, user, data):
        if not user.perfil_completo or user.talla_m is None:
            raise HTTPException(409, "Completa el perfil antes de registrar otra medición.")
        return self.repository.measurement(user, data.fecha, data.peso_kg)

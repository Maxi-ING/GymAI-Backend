from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.validation import Name
from app.modules.users.schemas import Email, Registration


class AdminSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.admin", env_prefix="ADMIN_", extra="ignore")
    nombre: Name = "Administrador"
    correo: Email
    clave: SecretStr

    def registration(self):
        return Registration(
            nombre=self.nombre, correo=self.correo, clave=self.clave.get_secret_value()
        )

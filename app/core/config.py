from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: SecretStr
    jwt_secret: SecretStr
    environment: Literal["development", "test", "production"] = "development"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]
    token_minutes: int = Field(default=60, ge=5, le=1440)
    auth_rate_limit: bool = True

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: SecretStr):
        if make_url(value.get_secret_value()).drivername not in {
            "postgresql",
            "postgres",
            "postgresql+psycopg",
        }:
            raise ValueError("DATABASE_URL debe corresponder a PostgreSQL.")
        return value

    @field_validator("jwt_secret")
    @classmethod
    def strong_secret(cls, value: SecretStr):
        secret = value.get_secret_value()
        if len(secret) < 32 or "REEMPLAZAR" in secret or "change-me" in secret.lower():
            raise ValueError("Genera un JWT_SECRET aleatorio de al menos 32 caracteres.")
        return value

    @model_validator(mode="after")
    def production_origins(self):
        if self.environment == "production" and (
            not self.cors_origins or any(not x.startswith("https://") for x in self.cors_origins)
        ):
            raise ValueError("En producción configura orígenes HTTPS exactos.")
        if any(x == "*" or x.endswith("/") for x in self.cors_origins):
            raise ValueError("CORS_ORIGINS requiere orígenes exactos, sin barra final.")
        return self

    @property
    def sqlalchemy_url(self):
        return make_url(self.database_url.get_secret_value()).set(drivername="postgresql+psycopg")


@lru_cache
def get_settings():
    return Settings()

from __future__ import annotations

from fastapi import HTTPException

from app.modules.records.models import Sesion
from app.modules.records.repository import RecordRepository
from app.modules.records.schemas import SessionInput
from app.modules.users.models import Usuario


class RecordService:
    """Aplica las reglas de negocio del registro de entrenamientos."""

    def __init__(self, repository: RecordRepository) -> None:
        """Recibe el repositorio de sesiones y catálogo."""
        self.repository = repository

    def create(self, user: Usuario, data: SessionInput) -> Sesion:
        """Valida perfil y ejercicios activos y prepara la sesión completa para su guardado."""
        if not user.perfil_completo:
            raise HTTPException(409, "Completa tu perfil antes de registrar entrenamientos.")
        ids = {row.ejercicio_id for row in data.registros}
        if len(self.repository.enabled_exercises(ids)) != len(ids):
            raise HTTPException(422, "Hay ejercicios inexistentes o inactivos.")
        return self.repository.create(user.id, data)

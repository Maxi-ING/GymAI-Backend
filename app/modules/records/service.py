from fastapi import HTTPException

from app.modules.records.repository import RecordRepository


class RecordService:
    def __init__(self, repository: RecordRepository):
        self.repository = repository

    def create(self, user, data):
        if not user.perfil_completo:
            raise HTTPException(409, "Completa tu perfil antes de registrar entrenamientos.")
        ids = {row.ejercicio_id for row in data.registros}
        if len(self.repository.enabled_exercises(ids)) != len(ids):
            raise HTTPException(422, "Hay ejercicios inexistentes o inactivos.")
        return self.repository.create(user.id, data)

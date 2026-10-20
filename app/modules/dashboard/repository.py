from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.predictions.models import Analisis
from app.modules.records.repository import RecordRepository
from app.modules.users.models import Medicion


class DashboardRepository:
    """Consulta los datos persistentes necesarios para el panel."""

    def __init__(self, db: Session) -> None:
        """Comparte la transacción con el repositorio de entrenamientos."""
        self.db = db
        self.records = RecordRepository(db)

    def last_measurement(self, user_id: int) -> Medicion | None:
        """Obtiene la medición más reciente por fecha e ID, o None."""
        return self.db.scalar(
            select(Medicion)
            .where(Medicion.usuario_id == user_id)
            .order_by(Medicion.fecha.desc(), Medicion.id.desc())
            .limit(1)
        )

    def last_analysis(self, user_id: int) -> Analisis | None:
        """Obtiene el último análisis guardado de la cuenta, sin ejecutar el modelo."""
        return self.db.scalar(
            select(Analisis)
            .where(Analisis.usuario_id == user_id)
            .order_by(Analisis.fecha.desc(), Analisis.id.desc())
            .limit(1)
        )

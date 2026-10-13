from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.predictions.models import Analisis
from app.modules.records.repository import RecordRepository
from app.modules.users.models import Medicion


class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db
        self.records = RecordRepository(db)

    def last_measurement(self, user_id):
        return self.db.scalar(
            select(Medicion)
            .where(Medicion.usuario_id == user_id)
            .order_by(Medicion.fecha.desc(), Medicion.id.desc())
            .limit(1)
        )

    def last_analysis(self, user_id):
        return self.db.scalar(
            select(Analisis)
            .where(Analisis.usuario_id == user_id)
            .order_by(Analisis.fecha.desc(), Analisis.id.desc())
            .limit(1)
        )

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.contracts import LoadMaximum, LoadRow
from app.modules.predictions.models import Analisis, Meta
from app.modules.predictions.schemas import AnalysisInput, GoalInput, Prediction
from app.modules.records.models import Ejercicio, Registro, Sesion


class PredictionRepository:
    """Consulta historial y metas y conserva los análisis solicitados."""

    def __init__(self, db: Session) -> None:
        """Usa la misma transacción que el servicio de análisis."""
        self.db = db

    def goals(self, user_id: int) -> list[Meta]:
        """Lista las metas de la cuenta ordenadas por ID."""
        return list(
            self.db.scalars(select(Meta).where(Meta.usuario_id == user_id).order_by(Meta.id))
        )

    def goal(self, user_id: int, goal_id: int, exercise_id: int) -> Meta | None:
        """Busca una meta que pertenezca tanto a la cuenta como al ejercicio."""
        return self.db.scalar(
            select(Meta).where(
                Meta.id == goal_id, Meta.usuario_id == user_id, Meta.ejercicio_id == exercise_id
            )
        )

    def exercise(self, exercise_id: int, active: bool = False) -> Ejercicio | None:
        """Busca un ejercicio y, si se exige activo, lo bloquea para una nueva meta."""
        query = select(Ejercicio).where(Ejercicio.id == exercise_id)
        if active:
            query = query.where(Ejercicio.activo.is_(True)).with_for_update(read=True)
        return self.db.scalar(query)

    def rows(self, user_id: int, exercise_id: int) -> list[LoadRow]:
        """Obtiene fecha, carga y repeticiones del ejercicio, respetando la cuenta."""
        return list(
            self.db.execute(
                select(Sesion.fecha, Registro.carga_kg, Registro.repeticiones)
                .join(Registro, Registro.sesion_id == Sesion.id)
                .where(Sesion.usuario_id == user_id, Registro.ejercicio_id == exercise_id)
                .order_by(Sesion.fecha, Sesion.id)
            )
        )

    def maxima(self, user_id: int) -> list[LoadMaximum]:
        """Agrupa las mejores cargas por ejercicio y repeticiones de la cuenta."""
        return list(
            self.db.execute(
                select(Registro.ejercicio_id, Registro.repeticiones, func.max(Registro.carga_kg))
                .join(Sesion, Sesion.id == Registro.sesion_id)
                .where(Sesion.usuario_id == user_id)
                .group_by(Registro.ejercicio_id, Registro.repeticiones)
            )
        )

    def add_goal(self, user_id: int, data: GoalInput) -> Meta:
        """Inserta una meta y asigna su ID sin confirmar la transacción."""
        item = Meta(usuario_id=user_id, **data.model_dump())
        self.db.add(item)
        self.db.flush()
        return item

    def save(self, user_id: int, data: AnalysisInput, result: Prediction) -> Analisis:
        """Guarda una instantánea JSON del resultado y de su versión."""
        item = Analisis(
            usuario_id=user_id,
            ejercicio_id=data.ejercicio_id,
            meta_id=data.meta_id,
            resultado=result.model_dump(mode="json"),
        )
        self.db.add(item)
        self.db.flush()
        return item

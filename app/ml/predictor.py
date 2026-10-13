import math
from abc import ABC, abstractmethod

import numpy as np
from sklearn.linear_model import LinearRegression

from app.modules.predictions.schemas import Prediction


class PredictorCarga(ABC):
    @abstractmethod
    def predecir(self, historial: list[dict], meta: float | None = None) -> Prediction:
        """Contrato independiente de SQLAlchemy, HTTP y scikit-learn."""


class PredictorLineal(PredictorCarga):
    def predecir(self, historial, meta=None):
        base = {"semanas_observadas": len(historial), "historial": historial}
        if not historial:
            return Prediction(
                estado="historial_insuficiente",
                mensaje="Registra al menos cuatro semanas del mismo ejercicio.",
                **base,
            )
        if meta is not None and max(p["carga_kg"] for p in historial) >= meta:
            return Prediction(
                estado="meta_alcanzada",
                mensaje="Ya registraste una carga igual o superior a esta meta.",
                **base,
            )
        if len(historial) < 4:
            return Prediction(
                estado="historial_insuficiente",
                mensaje="Se requieren cuatro semanas distintas con registros para estimar una tendencia.",
                **base,
            )
        x = np.array([p["semana"] for p in historial], dtype=float).reshape(-1, 1)
        y = np.array([p["carga_kg"] for p in historial], dtype=float)
        if not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("El historial contiene valores no finitos.")
        model = LinearRegression().fit(x, y)
        slope = float(model.coef_[0])
        if slope <= 1e-9:
            return Prediction(
                estado="sin_tendencia_positiva",
                mensaje="No hay una tendencia positiva suficiente para estimar una fecha de logro.",
                pendiente_kg_semana=round(slope, 4),
                **base,
            )
        last = historial[-1]["semana"]
        next_load = float(model.predict([[last + 1]])[0])
        current_fitted = float(model.predict([[last]])[0])
        eta = max(0.0, (meta - current_fitted) / slope) if meta is not None else None
        if not math.isfinite(next_load) or (eta is not None and not math.isfinite(eta)):
            raise ValueError("El resultado de la proyección no es finito.")
        # El gráfico muestra cuatro semanas; una fecha distante no se presenta como certeza.
        horizon = min(12, max(4, math.ceil(eta) if eta is not None else 4))
        projection = [
            {"semana": w, "carga_kg": round(float(model.predict([[w]])[0]), 2)}
            for w in range(last, last + horizon + 1)
        ]
        return Prediction(
            estado="estimado",
            mensaje="La tendencia estimada es positiva. Es una referencia matemática, no una indicación de cuánto levantar.",
            pendiente_kg_semana=round(slope, 4),
            siguiente_carga_kg=round(next_load, 2),
            semanas_hasta_meta=round(eta, 2) if eta is not None else None,
            proyeccion=projection,
            **base,
        )

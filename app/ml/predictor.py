import math
from abc import ABC, abstractmethod

import numpy as np
from sklearn.linear_model import LinearRegression

from app.modules.predictions.schemas import Prediction

MODEL_VERSION = "lineal_comparable_v2"
MAX_WEEKS = 12
MAX_LOAD = 600


class PredictorCarga(ABC):
    @abstractmethod
    def predecir(self, historial: list[dict], meta: float | None = None) -> Prediction:
        """Contrato independiente de SQLAlchemy, HTTP y scikit-learn."""


class PredictorLineal(PredictorCarga):
    def predecir(self, historial, meta=None):
        base = {
            "semanas_observadas": len(historial),
            "historial": historial,
            "modelo_version": MODEL_VERSION,
        }

        def result(state, message, **values):
            return Prediction(estado=state, mensaje=message, **base, **values)

        if meta is not None and historial and max(p["carga_kg"] for p in historial) >= meta:
            return result(
                "meta_alcanzada",
                "Ya registraste esta carga con las repeticiones comparadas. Es un logro histórico, no una indicación de aumentar el peso.",
            )
        if len(historial) < 4:
            return result(
                "historial_insuficiente",
                "Se necesitan cuatro semanas distintas del mismo ejercicio y con las mismas repeticiones.",
            )
        x = np.array([p["semana"] for p in historial], dtype=float).reshape(-1, 1)
        y = np.array([p["carga_kg"] for p in historial], dtype=float)
        if not np.isfinite(x).all() or not np.isfinite(y).all() or np.any(np.diff(x[:, 0]) <= 0):
            return result(
                "no_estimable",
                "No estimable con suficiente fiabilidad: revisa las fechas y los valores del historial.",
            )
        if np.max(np.diff(x[:, 0])) > 4:
            return result(
                "no_estimable",
                "No estimable con suficiente fiabilidad: hay intervalos de más de cuatro semanas sin registros comparables.",
            )

        # Cada punto se valida usando solo puntos anteriores, nunca datos futuros.
        errors, baseline_errors = [], []
        for end in range(2, len(historial)):
            trial = LinearRegression().fit(x[:end], y[:end])
            errors.append(abs(float(trial.predict(x[end : end + 1])[0]) - y[end]))
            baseline_errors.append(abs(float(y[end - 1] - y[end])))
        mae, baseline = float(np.mean(errors)), float(np.mean(baseline_errors))
        metrics = {
            "error_mae_kg": round(mae, 3),
            "error_referencia_kg": round(baseline, 3),
            "validaciones_temporales": len(errors),
        }
        model = LinearRegression().fit(x, y)
        slope = float(model.coef_[0])
        if slope <= 0:
            return result(
                "sin_tendencia_positiva",
                "No aparece una tendencia positiva. Se conserva el historial sin estimar una fecha de logro.",
                pendiente_kg_semana=round(slope, 4),
                **metrics,
            )
        # Umbrales operativos del curso: no son umbrales médicos ni confianza estadística.
        if slope < 0.05:
            return result(
                "no_estimable",
                "No estimable con suficiente fiabilidad: la variación es demasiado pequeña para calcular un plazo útil.",
                **metrics,
            )
        if mae > max(2.0, float(np.median(y)) * 0.10):
            return result(
                "no_estimable",
                "No estimable con suficiente fiabilidad: el error observado en semanas posteriores es demasiado alto.",
                **metrics,
            )
        if mae > baseline * 1.1 + 0.1:
            return result(
                "no_estimable",
                "No estimable con suficiente fiabilidad: la regresión no mejora suficientemente la referencia de repetir la última carga.",
                **metrics,
            )
        last = int(x[-1, 0])
        fitted = float(model.predict([[last]])[0])
        eta = (meta - fitted) / slope if meta is not None else None
        if eta is not None and (not math.isfinite(eta) or eta <= 0 or eta > MAX_WEEKS):
            return result(
                "no_estimable",
                "No estimable con suficiente fiabilidad: la meta queda fuera del horizonte de hasta doce semanas, o el ajuste no permite fecharla.",
                **metrics,
            )
        horizon = max(4, math.ceil(eta)) if eta is not None else 4
        projection = [
            {"semana": w, "carga_kg": round(float(model.predict([[w]])[0]), 2)}
            for w in range(last, last + horizon + 1)
        ]
        if any(
            not math.isfinite(p["carga_kg"]) or not 0 <= p["carga_kg"] <= MAX_LOAD
            for p in projection
        ):
            return result(
                "no_estimable",
                "No estimable con suficiente fiabilidad: la proyección sale del rango operativo de 0 a 600 kg.",
                **metrics,
            )
        return result(
            "estimado",
            "La tendencia supera las comprobaciones temporales del proyecto. Es una estimación del historial, no una indicación de cuánto levantar.",
            pendiente_kg_semana=round(slope, 4),
            siguiente_carga_kg=projection[1]["carga_kg"],
            semanas_hasta_meta=round(eta, 2) if eta is not None else None,
            proyeccion=projection,
            **metrics,
        )

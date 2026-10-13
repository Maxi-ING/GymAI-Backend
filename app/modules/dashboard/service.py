from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException

from app.modules.dashboard.repository import DashboardRepository
from app.modules.predictions.repository import PredictionRepository
from app.modules.predictions.service import goal_summary


class DashboardService:
    def __init__(self, repository: DashboardRepository):
        self.repository = repository

    def progress(self, user_id, exercise_id=None, desde=None, hasta=None):
        if desde and hasta and desde > hasta:
            raise HTTPException(422, "La fecha inicial debe ser anterior o igual a la final.")
        if exercise_id is not None and not PredictionRepository(self.repository.db).exercise(
            exercise_id
        ):
            raise HTTPException(404, "Ejercicio no disponible.")
        sessions = self.repository.records.sessions(user_id, desde, hasta)
        return self._progress(user_id, sessions, exercise_id)

    def _progress(self, user_id, sessions, exercise_id=None):
        points = {}
        count, volume, max_load = 0, Decimal(0), None
        for session in sessions:
            rows = [
                r for r in session.registros if exercise_id is None or r.ejercicio_id == exercise_id
            ]
            if not rows:
                continue
            count += 1
            point = points.setdefault(
                session.fecha,
                {"fecha": session.fecha, "carga_kg": Decimal(0), "volumen_kg": Decimal(0)},
            )
            for row in rows:
                work = row.dominio().volumen()
                point["volumen_kg"] += work
                point["carga_kg"] = max(point["carga_kg"], row.carga_kg)
                volume += work
                max_load = row.carga_kg if max_load is None else max(max_load, row.carga_kg)
        return {
            "total_sesiones": count,
            "volumen_total_kg": float(volume),
            "carga_maxima_kg": float(max_load) if max_load is not None else None,
            "ultima_medicion": self.repository.last_measurement(user_id),
            "puntos": list(points.values()),
        }

    def performance(self, user_id):
        return self._performance(self.repository.records.sessions(user_id))

    def _performance(self, sessions):
        grouped = defaultdict(list)
        for session in sessions:
            maximums = {}
            for row in session.registros:
                maximums[row.ejercicio_id] = max(
                    maximums.get(row.ejercicio_id, Decimal(0)), row.carga_kg
                )
            for exercise_id, load in maximums.items():
                grouped[exercise_id].append(float(load))
        names = {e.id: e.nombre for e in self.repository.records.exercises(active_only=False)}
        return [
            {
                "ejercicio_id": exercise_id,
                "nombre": names[exercise_id],
                "sesiones": len(loads),
                "primera_carga_kg": loads[0],
                "ultima_carga_kg": loads[-1],
                "mejor_carga_kg": max(loads),
                "variacion_porcentaje": round((loads[-1] - loads[0]) / loads[0] * 100, 2)
                if loads[0]
                else None,
            }
            for exercise_id, loads in sorted(grouped.items())
        ]

    def overview(self, user):
        sessions = self.repository.records.sessions(user.id)
        performance = self._performance(sessions)
        latest = {row["ejercicio_id"]: row["ultima_carga_kg"] for row in performance}
        best = {row["ejercicio_id"]: Decimal(str(row["mejor_carga_kg"])) for row in performance}
        goals = []
        for item in PredictionRepository(self.repository.db).goals(user.id):
            load = latest.get(item.ejercicio_id)
            goals.append(
                {
                    **goal_summary(item, best.get(item.ejercicio_id)),
                    "ejercicio_nombre": item.ejercicio.nombre,
                    "ultima_carga_kg": load,
                    "avance_porcentaje": min(
                        100, round(load / float(item.carga_objetivo_kg) * 100, 2)
                    )
                    if load is not None
                    else None,
                }
            )
        last = self.repository.last_analysis(user.id)
        recommendations = [
            {
                "titulo": "Mantén un historial completo",
                "mensaje": f"Tu objetivo es {user.objetivo or 'definir tu objetivo'}. Registra sesiones reales con series, repeticiones y carga para comparar el mismo ejercicio.",
                "origen": "regla",
                "accion": "registro",
            }
        ]
        if not user.perfil_completo:
            recommendations.append(
                {
                    "titulo": "Completa tu punto de partida",
                    "mensaje": "Actualiza edad, talla, peso y objetivo para disponer de tus indicadores corporales.",
                    "origen": "regla",
                    "accion": "perfil",
                }
            )
        elif not goals:
            recommendations.append(
                {
                    "titulo": "Define una meta de seguimiento",
                    "mensaje": "Acuerda una referencia de carga con tu entrenador y guárdala para seguir el avance.",
                    "origen": "regla",
                    "accion": "analisis",
                }
            )
        if last:
            recommendations.append(
                {
                    "titulo": "Revisa tu último análisis",
                    "mensaje": last.resultado["mensaje"],
                    "origen": "modelo",
                    "accion": "analisis",
                }
            )
        return {
            "progreso": self._progress(user.id, sessions),
            "rendimiento": performance,
            "metas": goals,
            "ultimo_analisis": {
                "ejercicio_nombre": last.ejercicio.nombre,
                "fecha": last.fecha,
                "resultado": last.resultado,
            }
            if last
            else None,
            "recomendaciones": recommendations,
        }

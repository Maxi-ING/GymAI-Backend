from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from decimal import Decimal


def weekly_loads(rows: Iterable[tuple[date, Decimal]]):
    rows = list(rows)
    if not rows:
        return []
    first = min(fecha for fecha, _ in rows)
    weekly = {}
    for fecha, carga in rows:
        week = (fecha - first).days // 7
        weekly[week] = max(weekly.get(week, Decimal(0)), carga)
    return [{"semana": week, "carga_kg": float(load)} for week, load in sorted(weekly.items())]


def comparable_loads(rows, repetitions=None):
    """Mismo ejercicio y mismas repeticiones, sin convertir a 1RM ni rellenar semanas.

    Si un cliente anterior no las indica, elegimos el grupo con más semanas,
    después el más reciente y, en empate, el de menos repeticiones.
    """
    groups = defaultdict(list)
    for fecha, carga, reps in rows:
        groups[reps].append((fecha, carga))
    if repetitions is None and groups:
        repetitions = max(
            groups,
            key=lambda reps: (
                len(weekly_loads(groups[reps])),
                max(fecha for fecha, _ in groups[reps]),
                -reps,
            ),
        )
    return weekly_loads(groups.get(repetitions, [])), repetitions

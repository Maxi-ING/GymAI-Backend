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

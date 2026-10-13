from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

from app.core.config import get_settings


class AuthLimiter:
    """Límite por proceso/IP. En varias réplicas usar un almacén compartido."""

    def __init__(self):
        self.events = defaultdict(deque)
        self.lock = Lock()

    def check(self, key: str):
        now = monotonic()
        with self.lock:
            # Evita conservar indefinidamente direcciones que ya no realizan solicitudes.
            if len(self.events) > 10000:
                self.events = defaultdict(
                    deque, {k: v for k, v in self.events.items() if v and v[-1] > now - 60}
                )
            queue = self.events[key]
            while queue and queue[0] <= now - 60:
                queue.popleft()
            if len(queue) >= 12:
                raise HTTPException(
                    429, "Demasiados intentos. Espera un minuto.", headers={"Retry-After": "60"}
                )
            queue.append(now)


limiter = AuthLimiter()


def auth_budget(request: Request):
    if get_settings().auth_rate_limit:
        limiter.check(request.client.host if request.client else "unknown")

import logging

from fastapi import Request
from sqlalchemy.exc import OperationalError, SQLAlchemyError

logger = logging.getLogger("fitanalytics.errors")


def connection_category(error: OperationalError) -> str:
    """Clasifica la causa de conexión sin copiar su mensaje al log."""
    message = str(error.orig).lower()
    categories = [
        ("password authentication failed", "autenticacion_rechazada"),
        ("tenant or user not found", "servidor_o_usuario_no_corresponde"),
        ("could not translate host name", "nombre_servidor_no_resuelve"),
        ("name or service not known", "nombre_servidor_no_resuelve"),
        ("timeout", "tiempo_conexion_agotado"),
        ("timed out", "tiempo_conexion_agotado"),
        ("certificate", "certificado_tls"),
        ("ssl", "conexion_tls"),
        ("connection refused", "conexion_rechazada"),
        ("network is unreachable", "red_no_disponible"),
        ("circuit breaker", "pooler_bloqueado_temporalmente"),
    ]
    return next(
        (name for pattern, name in categories if pattern in message), "conexion_no_clasificada"
    )


def report_internal_error(
    error: Exception,
    *,
    request: Request | None = None,
    event: str = "unexpected_error",
    status_code: int = 500,
) -> None:
    """Registra contexto técnico sin valores SQL, mensajes originales ni datos HTTP."""
    route = request.scope.get("route") if request is not None else None
    operation = f"{request.method} {getattr(route, 'path', '<sin_ruta>')}" if request else "interno"
    original = getattr(error, "orig", None) if isinstance(error, SQLAlchemyError) else None
    code = getattr(original, "sqlstate", None)
    safe_code = (
        code if isinstance(code, str) and len(code) == 5 and code.isalnum() else "sin_codigo"
    )
    category = connection_category(error) if isinstance(error, OperationalError) else event
    logger.log(
        logging.ERROR if status_code >= 500 else logging.WARNING,
        "event=%s operation=%s status=%s error_type=%s category=%s sqlstate=%s",
        event,
        operation,
        status_code,
        type(error).__name__,
        category,
        safe_code,
    )


def report_database_error(error: OperationalError, *, request: Request | None = None) -> None:
    """Conserva el diagnóstico de conexiones utilizando el formato común de errores."""
    report_internal_error(error, request=request, event="database_unavailable", status_code=503)

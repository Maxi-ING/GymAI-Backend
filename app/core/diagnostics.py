import logging

logger = logging.getLogger(__name__)


def report_database_error(error):
    original = error.orig
    message = str(original).lower()
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
    category = next(
        (name for pattern, name in categories if pattern in message), "conexion_no_clasificada"
    )
    code = getattr(original, "sqlstate", None)
    safe_code = (
        code if isinstance(code, str) and len(code) == 5 and code.isalnum() else "sin_codigo"
    )
    logger.error("PostgreSQL: categoria=%s sqlstate=%s", category, safe_code)

"""Respuestas de error y registro seguro compartidos por todos los módulos HTTP."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.core.diagnostics import report_database_error, report_internal_error


def install_error_handlers(app: FastAPI) -> None:
    """Instala los manejadores antes de CORS para conservar sus cabeceras en los fallos."""

    @app.middleware("http")
    async def unexpected_error(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # La captura evita que Uvicorn vuelva a imprimir la excepción original con sus valores.
        try:
            return await call_next(request)
        except Exception as error:
            report_internal_error(error, request=request)
            return JSONResponse(
                status_code=500,
                content={"detail": "Ocurrió un error interno. Intenta nuevamente."},
            )

    @app.exception_handler(IntegrityError)
    async def integrity_error(request: Request, error: IntegrityError) -> JSONResponse:
        report_internal_error(error, request=request, event="integrity_conflict", status_code=409)
        return JSONResponse(
            status_code=409,
            content={"detail": "La operación entra en conflicto con los datos existentes."},
        )

    @app.exception_handler(OperationalError)
    async def database_error(request: Request, error: OperationalError) -> JSONResponse:
        report_database_error(error, request=request)
        return JSONResponse(
            status_code=503,
            content={"detail": "La base de datos no está disponible. Intenta nuevamente."},
        )

    @app.exception_handler(SQLAlchemyError)
    async def persistence_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
        report_internal_error(error, request=request, event="persistence_error")
        return JSONResponse(
            status_code=500,
            content={"detail": "No se pudo completar la operación. Intenta nuevamente."},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in error.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

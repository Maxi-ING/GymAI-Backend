from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.config import get_settings
from app.core.database import engine

settings = get_settings()
app = FastAPI(
    title="FitAnalytics AI",
    version="0.1.0",
    description="API del gimnasio. Login JSON; pega el token Bearer en Authorize.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(IntegrityError)
def integrity_error(request, exc):
    return JSONResponse(
        status_code=409,
        content={"detail": "La operación entra en conflicto con los datos existentes."},
    )


@app.exception_handler(OperationalError)
def database_error(request, exc):
    return JSONResponse(
        status_code=503,
        content={"detail": "La base de datos no está disponible. Intenta nuevamente."},
    )


@app.get("/health", tags=["Disponibilidad"])
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}

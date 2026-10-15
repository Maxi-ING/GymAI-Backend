from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.config import get_settings
from app.core.database import engine
from app.core.diagnostics import report_database_error
from app.modules.admin.router import router as admin_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.predictions.router import router as predictions_router
from app.modules.records.router import router as records_router
from app.modules.users.router import router as users_router

settings = get_settings()
app = FastAPI(
    title="FitAnalytics AI",
    version="0.2.0",
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
    report_database_error(exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "La base de datos no está disponible. Intenta nuevamente."},
    )


@app.get("/health", tags=["Disponibilidad"])
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


app.include_router(users_router)
app.include_router(records_router)

app.include_router(dashboard_router)
app.include_router(predictions_router)

app.include_router(admin_router)


@app.exception_handler(RequestValidationError)
def validation_error(request, exc):
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})

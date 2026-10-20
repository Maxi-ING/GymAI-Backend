from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import install_error_handlers
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
install_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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

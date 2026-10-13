"""Datos exclusivos de pruebas; el comando se niega a usar una base real."""

from sqlalchemy import text

from app.cli import create_admin, seed_catalog
from app.core.config import get_settings
from app.core.database import Base, SessionFactory, engine, load_models
from app.modules.users.schemas import Registration

if get_settings().environment != "test" or not engine.url.database.endswith("_test"):
    raise RuntimeError("Solo se admite una base de pruebas cuyo nombre termina en _test.")
load_models()
with SessionFactory.begin() as db:
    db.execute(
        text(
            "TRUNCATE "
            + ", ".join(f'gym_app."{t.name}"' for t in Base.metadata.sorted_tables)
            + " RESTART IDENTITY CASCADE"
        )
    )
    seed_catalog(db)
    create_admin(
        db,
        Registration(
            nombre="Admin Pruebas",
            correo="browser-admin@example.com",
            clave="Browser-Testing-Only-123",
        ),
    )

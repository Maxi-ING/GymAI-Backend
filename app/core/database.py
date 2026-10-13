from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import get_settings

SCHEMA = "gym_app"

class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA, naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })

engine = create_engine(get_settings().sqlalchemy_url, pool_pre_ping=True, pool_size=5,
                       max_overflow=2, pool_timeout=15, hide_parameters=True,
                       connect_args={"connect_timeout": 10})
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

def get_db():
    # Una sesión por solicitud. El error revierte todo el trabajo pendiente.
    with SessionFactory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

def load_models():
    from app.modules.users import models as users
    from app.modules.records import models as records
    from app.modules.predictions import models as predictions
    from app.modules.admin import models as admin
    return users, records, predictions, admin

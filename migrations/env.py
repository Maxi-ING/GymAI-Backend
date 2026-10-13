from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.core.database import SCHEMA, Base, load_models

load_models()
target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == SCHEMA
    return True


def configure(connection=None, url=None):
    context.configure(
        connection=connection,
        url=url,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        compare_type=True,
        version_table_schema=SCHEMA,
        literal_binds=connection is None,
    )


if context.is_offline_mode():
    configure(url=get_settings().sqlalchemy_url)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(
        get_settings().sqlalchemy_url, poolclass=pool.NullPool, hide_parameters=True
    )
    with engine.connect() as connection:
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS gym_app")
        connection.commit()
        configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()

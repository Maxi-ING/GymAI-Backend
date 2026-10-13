"""Reservar el esquema del gimnasio al backend."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TABLES = (
    "usuarios",
    "mediciones",
    "ejercicios",
    "sesiones",
    "registros",
    "metas",
    "analisis",
    "auditoria",
)


def upgrade():
    for role in ("PUBLIC", "anon", "authenticated"):
        statements = [
            f"REVOKE ALL ON SCHEMA gym_app FROM {role}",
            f"REVOKE ALL ON ALL TABLES IN SCHEMA gym_app FROM {role}",
            f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA gym_app FROM {role}",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA gym_app REVOKE ALL ON TABLES FROM {role}",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA gym_app REVOKE ALL ON SEQUENCES FROM {role}",
        ]
        if role == "PUBLIC":
            for statement in statements:
                op.execute(statement)
        else:
            # PostgreSQL local no incluye los roles propios de Supabase.
            commands = "; ".join(statements)
            op.execute(
                f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') "
                f"THEN {commands}; END IF; END $$"
            )
    for table in TABLES:
        op.execute(f"ALTER TABLE gym_app.{table} ENABLE ROW LEVEL SECURITY")


def downgrade():
    # No reabre acceso público al revertir: conserva los REVOKE.
    for table in TABLES:
        op.execute(f"ALTER TABLE gym_app.{table} DISABLE ROW LEVEL SECURITY")

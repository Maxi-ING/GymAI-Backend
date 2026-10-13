"""Completar índices de las relaciones del gimnasio."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

INDEXES = (
    ("analisis", "ejercicio_id"),
    ("analisis", "meta_id"),
    ("auditoria", "actor_id"),
    ("metas", "ejercicio_id"),
    ("registros", "ejercicio_id"),
)


def upgrade():
    for table, column in INDEXES:
        op.create_index(f"ix_{table}_{column}", table, [column], schema="gym_app")


def downgrade():
    for table, column in reversed(INDEXES):
        op.drop_index(f"ix_{table}_{column}", table_name=table, schema="gym_app")

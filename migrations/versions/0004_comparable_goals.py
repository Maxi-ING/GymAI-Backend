"""Añadir repeticiones opcionales a las metas sin reinterpretar las existentes."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "metas", sa.Column("repeticiones_objetivo", sa.Integer(), nullable=True), schema="gym_app"
    )
    op.create_check_constraint(
        op.f("ck_metas_repeticiones"),
        "metas",
        "repeticiones_objetivo IS NULL OR repeticiones_objetivo BETWEEN 1 AND 100",
        schema="gym_app",
    )


def downgrade():
    op.drop_constraint(op.f("ck_metas_repeticiones"), "metas", schema="gym_app", type_="check")
    op.drop_column("metas", "repeticiones_objetivo", schema="gym_app")

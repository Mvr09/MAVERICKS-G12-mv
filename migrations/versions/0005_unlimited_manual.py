"""Autorización manual sin cupo, conservando contadores históricos."""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "consumption_budgets",
        "request_limit",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "consumption_budgets",
        "window_seconds",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "grants", "article_limit", existing_type=sa.Integer(), nullable=True
    )


def downgrade():
    raise RuntimeError("Cambio de autorizaciones: requiere migración explícita")

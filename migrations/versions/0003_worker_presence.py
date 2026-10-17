"""Presencia del worker para distinguir una cola pendiente de un servicio caído."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "worker_presence",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("heartbeat", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    raise RuntimeError("Borrado de datos: requiere autorización y migración explícita")

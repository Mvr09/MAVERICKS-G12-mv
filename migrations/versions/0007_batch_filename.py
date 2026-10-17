"""Procedencia del archivo importado, sin exponer originales."""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("batches", sa.Column("filename", sa.String(), nullable=True))


def downgrade():
    op.drop_column("batches", "filename")

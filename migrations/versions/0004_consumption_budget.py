"""Presupuesto HTTP compartido y persistente entre lotes autorizados."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("worker_presence", sa.Column("revision", sa.String(), nullable=True))
    op.create_table(
        "consumption_budgets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("request_limit", sa.Integer(), nullable=False),
        sa.Column("requests_used", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
    )
    op.add_column("grants", sa.Column("budget_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "grants_budget_fk", "grants", "consumption_budgets", ["budget_id"], ["id"]
    )
    op.add_column("api_calls", sa.Column("budget_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "api_calls_budget_fk", "api_calls", "consumption_budgets", ["budget_id"], ["id"]
    )
    op.add_column("batches", sa.Column("export_headers", sa.JSON(), nullable=True))
    op.create_table(
        "import_rows",
        sa.Column(
            "article_id", sa.String(), sa.ForeignKey("articles.id"), primary_key=True
        ),
        sa.Column("data", sa.JSON(), nullable=False),
    )


def downgrade():
    raise RuntimeError("Borrado de datos: requiere autorización y migración explícita")

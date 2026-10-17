"""Reanálisis versionado y contraste RSS sin alterar resultados del ejercicio."""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "articles",
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "analyses",
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "api_calls",
        sa.Column("run_key", sa.String(), nullable=False, server_default=""),
    )
    op.create_table(
        "comparisons",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "article_id", sa.String(), sa.ForeignKey("articles.id"), nullable=False
        ),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("ballots", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_comparisons_article_id", "comparisons", ["article_id"])
    op.create_table(
        "rss_daily_usage",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Preservar el consumo RSS ya reservado incluso si después se borran noticias.
    from app.importer import digest

    rows = op.get_bind().execute(
        sa.text(
            "SELECT a.origin_key, a.content_hash, g.reserved_at FROM grant_articles g JOIN articles a ON a.id=g.article_id WHERE a.context='rss'"
        )
    )
    for origin, content, reserved in rows:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO rss_daily_usage(id,reserved_at) VALUES (:id,:at) ON CONFLICT DO NOTHING"
            ),
            {
                "id": digest([reserved.date().isoformat(), origin, content]),
                "at": reserved,
            },
        )


def downgrade():
    raise RuntimeError("Borrado de historial: requiere migración explícita")

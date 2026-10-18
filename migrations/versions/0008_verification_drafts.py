"""Add source-backed verification drafts without requiring a risk incident."""
from alembic import op
import sqlalchemy as sa
revision='0008'
down_revision='0007'
branch_labels=None
depends_on=None

def upgrade():
    op.alter_column('drafts','incident_id',existing_type=sa.String(),nullable=True)
    op.add_column('drafts',sa.Column('article_id',sa.String(),sa.ForeignKey('articles.id'),nullable=True))
    op.add_column('drafts',sa.Column('evidence_snapshot',sa.JSON(),nullable=True))

def downgrade():
    if op.get_bind().execute(sa.text('SELECT 1 FROM drafts WHERE incident_id IS NULL LIMIT 1')).first():
        raise RuntimeError('Conserva los borradores de verificación antes de revertir; no se eliminan automáticamente.')
    op.drop_column('drafts','evidence_snapshot')
    op.drop_column('drafts','article_id')
    op.alter_column('drafts','incident_id',existing_type=sa.String(),nullable=False)

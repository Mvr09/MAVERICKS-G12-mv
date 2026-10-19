"""Human decisions and incident work, isolated from model evaluation."""
from alembic import op
import sqlalchemy as sa
revision='0009'
down_revision='0008'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('human_decisions',sa.Column('id',sa.String(),primary_key=True),sa.Column('article_id',sa.String(),sa.ForeignKey('articles.id'),nullable=False),sa.Column('supplier_id',sa.String(),sa.ForeignKey('suppliers.id'),nullable=False),sa.Column('analysis_id',sa.String(),sa.ForeignKey('analyses.id'),nullable=False),sa.Column('generation',sa.Integer(),nullable=False),sa.Column('source_version',sa.Integer(),nullable=False),sa.Column('content_hash',sa.String(),nullable=False),sa.Column('data',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_human_decisions_article_id','human_decisions',['article_id']);op.create_index('ix_human_decisions_supplier_id','human_decisions',['supplier_id'])
    op.create_table('incident_work',sa.Column('id',sa.String(),primary_key=True),sa.Column('incident_id',sa.String(),sa.ForeignKey('incidents.id'),nullable=False),sa.Column('data',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False));op.create_index('ix_incident_work_incident_id','incident_work',['incident_id'])

def downgrade():
    bind=op.get_bind()
    if bind.execute(sa.text('SELECT 1 FROM human_decisions LIMIT 1')).first() or bind.execute(sa.text('SELECT 1 FROM incident_work LIMIT 1')).first():raise RuntimeError('Conservar decisiones humanas y acciones antes de revertir; no se borran automáticamente.')
    op.drop_table('incident_work');op.drop_table('human_decisions')

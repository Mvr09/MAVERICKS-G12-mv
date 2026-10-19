"""Isolated comparative evaluation, no operational effects."""
from alembic import op
import sqlalchemy as sa
revision='0010'
down_revision='0009'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('evaluation_campaigns',sa.Column('id',sa.String(),primary_key=True),sa.Column('name',sa.String(),nullable=False),sa.Column('freeze',sa.JSON(),nullable=False),sa.Column('state',sa.String(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('started_at',sa.DateTime(timezone=True)),sa.Column('completed_at',sa.DateTime(timezone=True)))
    op.create_table('campaign_runs',sa.Column('id',sa.String(),primary_key=True),sa.Column('campaign_id',sa.String(),sa.ForeignKey('evaluation_campaigns.id'),nullable=False),sa.Column('profile',sa.String(),nullable=False),sa.Column('input_key',sa.String(),nullable=False),sa.Column('split',sa.String(),nullable=False),sa.Column('source',sa.JSON(),nullable=False),sa.Column('reference',sa.JSON()),sa.Column('state',sa.String(),nullable=False),sa.Column('result',sa.JSON()),sa.Column('audit',sa.JSON(),nullable=False),sa.Column('started_at',sa.DateTime(timezone=True)),sa.Column('completed_at',sa.DateTime(timezone=True)),sa.UniqueConstraint('campaign_id','profile','input_key'))
    op.create_index('ix_campaign_runs_campaign_id','campaign_runs',['campaign_id'])

def downgrade():
    if op.get_bind().execute(sa.text('select 1 from evaluation_campaigns limit 1')).first():raise RuntimeError('Preservar campañas; no se borran resultados para revertir.')
    op.drop_table('campaign_runs');op.drop_table('evaluation_campaigns')

"""Suggested action plans per incident revision, drafted with Claude or a template."""
from alembic import op
import sqlalchemy as sa
revision='0011'
down_revision='0010'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('action_plans',sa.Column('id',sa.String(),primary_key=True),sa.Column('incident_id',sa.String(),sa.ForeignKey('incidents.id'),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),sa.Column('rules_version',sa.String(),nullable=False),sa.Column('facts',sa.JSON(),nullable=False),sa.Column('actions',sa.JSON(),nullable=False),sa.Column('facts_hash',sa.String(),nullable=False),sa.Column('summary_template',sa.Text(),nullable=False),sa.Column('summary_llm',sa.Text()),sa.Column('summary_source',sa.String(),nullable=False),sa.Column('summary_error',sa.String()),sa.Column('llm',sa.JSON()),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint('incident_id','revision'))
    op.create_index('ix_action_plans_incident_id','action_plans',['incident_id'])

def downgrade():
    # Plans are derived suggestions; incidents, alerts and human follow-up stay intact.
    op.drop_table('action_plans')

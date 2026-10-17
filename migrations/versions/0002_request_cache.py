"""Durable API cache and consumption reservations."""
from alembic import op
from app.models import RequestCache,GrantArticle
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
    RequestCache.__table__.create(op.get_bind(),checkfirst=True)
    GrantArticle.__table__.create(op.get_bind(),checkfirst=True)
def downgrade(): raise RuntimeError('Destructivo: requiere autorización específica')

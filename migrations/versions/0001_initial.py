"""Initial durable radar schema."""
from alembic import op
from app.db import Base
from app import models
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade(): Base.metadata.create_all(bind=op.get_bind())
def downgrade():
    raise RuntimeError('El borrado del esquema requiere una autorización específica y una migración explícita.')

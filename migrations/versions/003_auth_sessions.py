"""Persist revocable sessions and distributed login throttles."""
from alembic import op
import sqlalchemy as sa
revision='003'
down_revision='002'
def upgrade():
    op.create_table('auth_sessions',sa.Column('id',sa.String(),primary_key=True),sa.Column('user_id',sa.String(),sa.ForeignKey('users.id'),nullable=False),sa.Column('expires_at',sa.Integer(),nullable=False),sa.Column('revoked',sa.Boolean(),nullable=False))
    op.create_index('ix_auth_sessions_user_id','auth_sessions',['user_id'])
    op.create_index('ix_auth_sessions_expires_at','auth_sessions',['expires_at'])
    op.create_table('auth_throttles',sa.Column('id',sa.String(),primary_key=True),sa.Column('failures',sa.Integer(),nullable=False),sa.Column('window_started',sa.Integer(),nullable=False))
def downgrade():
    op.drop_table('auth_throttles'); op.drop_table('auth_sessions')

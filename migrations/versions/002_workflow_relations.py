"""Frozen relational schema migration."""
from alembic import op
import sqlalchemy as sa
revision='002'
down_revision='001'
def upgrade():
    op.create_table('purchase_requisitions',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_table('users',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('role', sa.String(), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_table('chat_messages',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('chat_id', sa.String(), sa.ForeignKey('chat_sessions.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_chat_messages_chat_id', 'chat_messages', ['chat_id'])
    op.create_table('policy_approvals',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('policy_id', sa.String(), sa.ForeignKey('policy_versions.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_policy_approvals_policy_id', 'policy_approvals', ['policy_id'])
    op.create_table('pr_lines',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('requisition_id', sa.String(), sa.ForeignKey('purchase_requisitions.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_pr_lines_requisition_id', 'pr_lines', ['requisition_id'])
    op.create_table('purchase_order_lines',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('order_id', sa.String(), sa.ForeignKey('purchase_orders.id'), primary_key=False, nullable=False),
        sa.Column('requirement_id', sa.String(), sa.ForeignKey('run_requirements.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_purchase_order_lines_order_id', 'purchase_order_lines', ['order_id'])
    op.create_index('ix_purchase_order_lines_requirement_id', 'purchase_order_lines', ['requirement_id'])
    op.create_table('requirement_pr_membership',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('requirement_id', sa.String(), sa.ForeignKey('run_requirements.id'), primary_key=False, nullable=False),
        sa.Column('pr_line_id', sa.String(), sa.ForeignKey('pr_lines.id'), primary_key=False, nullable=False),
    )
    op.create_index('ix_requirement_pr_membership_pr_line_id', 'requirement_pr_membership', ['pr_line_id'])
    op.create_index('ix_requirement_pr_membership_requirement_id', 'requirement_pr_membership', ['requirement_id'])
def downgrade():
    op.drop_table('requirement_pr_membership')
    op.drop_table('purchase_order_lines')
    op.drop_table('pr_lines')
    op.drop_table('policy_approvals')
    op.drop_table('chat_messages')
    op.drop_table('users')
    op.drop_table('purchase_requisitions')

"""Frozen relational schema migration."""
from alembic import op
import sqlalchemy as sa
revision='001'
down_revision=None
def upgrade():
    op.create_table('approved_pr_lines',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('action_id', sa.String(), primary_key=False, nullable=False),
    )
    op.create_table('audit_events',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('created_at', sa.String(), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_audit_events_created_at', 'audit_events', ['created_at'])
    op.create_table('buyer_overrides',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_table('chat_sessions',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_table('contract_proposals',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_table('data_snapshots',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_table('items',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_table('plants',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_table('policy_versions',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('status', sa.String(), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_policy_versions_status', 'policy_versions', ['status'])
    op.create_table('suppliers',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_table('contracts',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('supplier_id', sa.String(), sa.ForeignKey('suppliers.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_contracts_supplier_id', 'contracts', ['supplier_id'])
    op.create_table('historical_po_lines',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('item_id', sa.String(), sa.ForeignKey('items.id'), primary_key=False, nullable=False),
        sa.Column('supplier_id', sa.String(), sa.ForeignKey('suppliers.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_historical_po_lines_item_id', 'historical_po_lines', ['item_id'])
    op.create_index('ix_historical_po_lines_supplier_id', 'historical_po_lines', ['supplier_id'])
    op.create_table('processing_runs',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('created_at', sa.String(), primary_key=False, nullable=False),
        sa.Column('input_hash', sa.String(), primary_key=False, nullable=False),
        sa.Column('data_hash', sa.String(), sa.ForeignKey('data_snapshots.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_processing_runs_input_hash', 'processing_runs', ['input_hash'])
    op.create_table('contract_ledger',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('contract_id', sa.String(), sa.ForeignKey('contracts.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_contract_ledger_contract_id', 'contract_ledger', ['contract_id'])
    op.create_table('contract_lines',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('contract_id', sa.String(), sa.ForeignKey('contracts.id'), primary_key=False, nullable=False),
        sa.Column('item_id', sa.String(), sa.ForeignKey('items.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_contract_lines_contract_id', 'contract_lines', ['contract_id'])
    op.create_index('ix_contract_lines_item_id', 'contract_lines', ['item_id'])
    op.create_table('purchase_orders',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('run_id', sa.String(), sa.ForeignKey('processing_runs.id'), primary_key=False, nullable=False),
        sa.Column('supplier_id', sa.String(), sa.ForeignKey('suppliers.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_purchase_orders_run_id', 'purchase_orders', ['run_id'])
    op.create_table('run_requirements',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('run_id', sa.String(), sa.ForeignKey('processing_runs.id'), primary_key=False, nullable=False),
        sa.Column('group_id', sa.String(), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_index('ix_run_requirements_group_id', 'run_requirements', ['group_id'])
    op.create_index('ix_run_requirements_run_id', 'run_requirements', ['run_id'])
    op.create_table('sourcing_requests',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('run_id', sa.String(), sa.ForeignKey('processing_runs.id'), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
    )
def downgrade():
    op.drop_table('sourcing_requests')
    op.drop_table('run_requirements')
    op.drop_table('purchase_orders')
    op.drop_table('contract_lines')
    op.drop_table('contract_ledger')
    op.drop_table('processing_runs')
    op.drop_table('historical_po_lines')
    op.drop_table('contracts')
    op.drop_table('suppliers')
    op.drop_table('policy_versions')
    op.drop_table('plants')
    op.drop_table('items')
    op.drop_table('data_snapshots')
    op.drop_table('contract_proposals')
    op.drop_table('chat_sessions')
    op.drop_table('buyer_overrides')
    op.drop_table('audit_events')
    op.drop_table('approved_pr_lines')

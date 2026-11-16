"""Versioned local knowledge, bounded chat turns and metered AI usage."""
from alembic import op
import sqlalchemy as sa

revision='004'
down_revision='003'

def upgrade():
    op.create_table('knowledge_documents',sa.Column('id',sa.String(),primary_key=True),sa.Column('source_key',sa.String(),nullable=False),sa.Column('source_hash',sa.String(),nullable=False),sa.Column('owner_id',sa.String(),sa.ForeignKey('users.id')),sa.Column('classification',sa.String(),nullable=False),sa.Column('status',sa.String(),nullable=False),sa.Column('updated_at',sa.String(),nullable=False),sa.Column('payload',sa.JSON(),nullable=False),sa.UniqueConstraint('source_key','source_hash',name='uq_knowledge_source_revision'))
    for column in ['source_key','source_hash','owner_id','classification','status']:op.create_index('ix_knowledge_documents_'+column,'knowledge_documents',[column])
    op.create_table('knowledge_chunks',sa.Column('id',sa.String(),primary_key=True),sa.Column('document_id',sa.String(),sa.ForeignKey('knowledge_documents.id'),nullable=False),sa.Column('ordinal',sa.Integer(),nullable=False),sa.Column('content',sa.Text(),nullable=False),sa.Column('content_hash',sa.String(),nullable=False),sa.Column('embedding',sa.JSON()),sa.Column('embedding_model',sa.String()),sa.Column('payload',sa.JSON(),nullable=False),sa.UniqueConstraint('document_id','ordinal',name='uq_knowledge_chunk_position'))
    op.create_index('ix_knowledge_chunks_document_id','knowledge_chunks',['document_id'])
    op.create_table('chat_turns',sa.Column('id',sa.String(),primary_key=True),sa.Column('chat_id',sa.String(),sa.ForeignKey('chat_sessions.id'),nullable=False),sa.Column('actor',sa.String(),sa.ForeignKey('users.id'),nullable=False),sa.Column('request_hash',sa.String(),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),sa.Column('status',sa.String(),nullable=False),sa.Column('expires_at',sa.Integer(),nullable=False),sa.Column('response',sa.JSON()),sa.Column('payload',sa.JSON(),nullable=False))
    for column in ['chat_id','actor','status']:op.create_index('ix_chat_turns_'+column,'chat_turns',[column])
    op.create_table('ai_usage',sa.Column('id',sa.String(),primary_key=True),sa.Column('actor',sa.String(),sa.ForeignKey('users.id'),nullable=False),sa.Column('created_at',sa.String(),nullable=False),sa.Column('model',sa.String(),nullable=False),sa.Column('status',sa.String(),nullable=False),sa.Column('input_tokens',sa.Integer(),nullable=False),sa.Column('output_tokens',sa.Integer(),nullable=False),sa.Column('cost_usd',sa.String(),nullable=False),sa.Column('payload',sa.JSON(),nullable=False))
    for column in ['actor','created_at']:op.create_index('ix_ai_usage_'+column,'ai_usage',[column])
    op.create_table('ai_budgets',sa.Column('id',sa.String(),primary_key=True),sa.Column('tokens',sa.Integer(),nullable=False),sa.Column('cost_usd',sa.String(),nullable=False))
    if op.get_bind().dialect.name=='postgresql':
        op.execute("CREATE INDEX ix_knowledge_chunks_search ON knowledge_chunks USING gin (to_tsvector('simple', content))")
        # Optional vector support never makes ordinary procurement migrations
        # depend on a managed provider granting extension-creation privileges.
        connection=op.get_bind()
        available=connection.scalar(sa.text("SELECT 1 FROM pg_available_extensions WHERE name='vector'"))
        if available:
            try:
                with connection.begin_nested():connection.execute(sa.text('CREATE EXTENSION IF NOT EXISTS vector'))
            except sa.exc.DBAPIError:pass
        schema=connection.scalar(sa.text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'"))
        if schema:
            quoted=connection.dialect.identifier_preparer.quote(schema)
            op.execute(f'ALTER TABLE knowledge_chunks ADD COLUMN embedding_vector {quoted}.vector(1536)')
            op.execute(f'CREATE INDEX ix_knowledge_chunks_vector ON knowledge_chunks USING hnsw (embedding_vector {quoted}.vector_cosine_ops) WHERE embedding_vector IS NOT NULL')

def downgrade():
    for table in ['ai_budgets','ai_usage','chat_turns','knowledge_chunks','knowledge_documents']:op.drop_table(table)

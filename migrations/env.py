from alembic import context
from sqlalchemy import text
from backend.db import Base,connect
engine,_=connect()
with engine.connect() as connection:
    context.configure(connection=connection,target_metadata=Base.metadata)
    with context.begin_transaction():
        if engine.dialect.name=='postgresql': connection.execute(text('SELECT pg_advisory_xact_lock(135792468)'))
        context.run_migrations()

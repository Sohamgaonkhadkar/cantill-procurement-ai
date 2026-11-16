from alembic.config import Config
from alembic import command
from sqlalchemy import inspect
from backend.db import Base,connect

def test_clean_migration_and_repeat_upgrade(tmp_path,monkeypatch):
    url='sqlite:///'+str(tmp_path/'migrations.db')
    monkeypatch.setenv('DATABASE_URL',url)
    cfg=Config('alembic.ini'); command.upgrade(cfg,'head'); command.upgrade(cfg,'head')
    engine,_=connect(url)
    assert set(inspect(engine).get_table_names())==set(Base.metadata.tables)|{'alembic_version'}
    command.downgrade(cfg,'base')
    assert set(inspect(engine).get_table_names())=={'alembic_version'}
    engine.dispose()

from pathlib import Path
import pytest
from backend.db import connect
from test_api import client

def test_vercel_refuses_ephemeral_database(monkeypatch):
    monkeypatch.setenv('VERCEL','1'); monkeypatch.delenv('DATABASE_URL',raising=False)
    with pytest.raises(RuntimeError,match='Persistent DATABASE_URL'): connect()

def test_postgres_connect_does_not_write_local_files(monkeypatch):
    def reject(*args,**kwargs): raise AssertionError('Unexpected filesystem mutation')
    monkeypatch.setattr(Path,'mkdir',reject)
    engine,_=connect('postgresql+psycopg://example:example@localhost/example')
    assert engine.dialect.name=='postgresql'
    engine.dispose()

def test_final_deployment_refuses_missing_arena():
    from scripts.build_vercel import main
    if not Path('frontend/package.json').exists():
        with pytest.raises(RuntimeError,match='Arena frontend ZIP'): main()

def test_missing_frontend_assets_never_return_spa_html(client):
    for path in ['/assets/old-release.js','/assets/old-release.css','/missing-image.png']:
        response=client.get(path)
        assert response.status_code==404
        assert response.headers['content-type'].startswith('application/json')
    response=client.get('/')
    assert response.status_code==200 and response.headers['cache-control']=='no-store'

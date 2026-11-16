import pytest
from backend import security
from backend.workspace import isolated_demo,check_workspace_database,DEMO_PASSWORDS
from backend.db import User
from backend import api
from test_api import client

DEMO_URL='postgresql+psycopg://corvo_demo_app:synthetic-test-password@demo.invalid/demo?options=-csearch_path%3Dcorvo_public_demo'

@pytest.mark.parametrize('url',[
    'postgresql://owner:password@demo.invalid/db',
    DEMO_URL.replace('corvo_demo_app','owner'),
    DEMO_URL.replace('corvo_public_demo','public'),
    DEMO_URL.replace('demo.invalid','demo-pooler.invalid'),
    'sqlite:///.private/demo.db',
])
def test_public_demo_rejects_nonisolated_database_configuration(monkeypatch,url):
    monkeypatch.setenv('WORKSPACE_MODE','demo')
    assert not isolated_demo(url)
    with pytest.raises(RuntimeError):check_workspace_database(url)

def test_demo_access_does_not_activate_on_live_workspace(monkeypatch):
    monkeypatch.setenv('WORKSPACE_MODE','live')
    monkeypatch.setenv('DATABASE_URL',DEMO_URL)
    monkeypatch.setenv('VERCEL','1')
    monkeypatch.setenv('SUBMISSION_ACCESS','true')
    assert not isolated_demo() and not security.submission_access()

def test_only_isolated_workspace_publishes_all_role_passwords(client,monkeypatch):
    monkeypatch.setenv('WORKSPACE_MODE','demo')
    monkeypatch.setenv('DATABASE_URL',DEMO_URL)
    monkeypatch.setenv('VERCEL','1')
    with api.Session.begin() as s:
        for role in DEMO_PASSWORDS:
            account=s.get(User,role)
            account.payload={**account.payload,'type':'public_demo_role','access_scope':'evaluation'}
    options=client.get('/api/auth/options').json()
    assert options['workspace_mode']=='demo' and options['submission_access']
    assert {p['role']:p['password'] for p in options['roles']}==DEMO_PASSWORDS
    for role,password in DEMO_PASSWORDS.items():
        session=client.post('/api/auth/login',json={'role':role,'password':password})
        assert session.status_code==200 and session.json()['role']==role
        headers={'Authorization':'Bearer '+session.json()['access_token']}
        assert client.get('/api/auth/me',headers=headers).json()['workspace_mode']=='demo'
        assert client.get('/api/users',headers=headers).status_code==403
    monkeypatch.setenv('WORKSPACE_MODE','live')
    options=client.get('/api/auth/options').json()
    assert options['roles']==[] and options['workspace_mode']=='live'
    for role,password in DEMO_PASSWORDS.items():
        assert client.post('/api/auth/login',json={'role':role,'password':password}).status_code==401

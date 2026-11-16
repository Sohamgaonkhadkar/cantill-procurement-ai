from backend import api
from backend.db import User
from test_api import client

PASSWORD='Synthetic-registration-12345'

def test_submission_access_explicit_opt_in_and_no_private_passwords(client,monkeypatch):
    monkeypatch.setenv('SUBMISSION_ACCESS','false')
    monkeypatch.setenv('PUBLIC_REGISTRATION','false')
    assert client.get('/api/auth/options').json()=={'submission_access':False,'registration_enabled':False,'roles':[]}
    assert client.post('/api/auth/login',json={'role':'buyer','password':'corvo-buyer-demo'}).status_code==401
    body={'username':'new-user','display_name':'New User','password':PASSWORD}
    assert client.post('/api/auth/register',json=body).status_code==403
    monkeypatch.setenv('SUBMISSION_ACCESS','true')
    options=client.get('/api/auth/options').json()
    assert not options['registration_enabled'] and options['roles']==[{'role':'requester','password':'corvo-requester-demo'}]
    for role in options['roles']:
        r=client.post('/api/auth/login',json=role)
        assert r.status_code==200 and r.json()['role']==role['role']
    monkeypatch.setenv('ADMIN_PASSWORD','Private-operational-password')
    assert 'Private-operational-password' not in client.get('/api/auth/options').text
    assert client.post('/api/auth/login',json={'role':'admin','password':'corvo-admin-demo'}).status_code==401
    assert client.post('/api/auth/login',json={'role':'buyer','password':'corvo-buyer-demo'}).status_code==401
    with api.Session.begin() as s:
        u=s.get(User,'buyer');u.payload={**u.payload,'enabled':False}
    assert client.post('/api/auth/login',json={'role':'buyer','password':'corvo-buyer-demo'}).status_code==401

def test_individual_registration_cannot_escalate_and_logs_in(client,monkeypatch):
    monkeypatch.setenv('PUBLIC_REGISTRATION','true')
    body={'username':'new-user','display_name':'New User','password':PASSWORD}
    assert client.post('/api/auth/register',json={**body,'role':'admin'}).status_code==422
    assert client.post('/api/auth/register',json={**body,'password':'short'}).status_code==422
    r=client.post('/api/auth/register',json=body)
    assert r.status_code==201 and r.json()['role']=='requester'
    headers={'Authorization':'Bearer '+r.json()['access_token']}
    assert client.get('/api/auth/me',headers=headers).json()['id']=='new-user'
    assert client.get('/api/users',headers=headers).status_code==403
    assert client.post('/api/auth/register',json=body).status_code==409
    assert client.post('/api/auth/login',json={'username':'new-user','password':PASSWORD}).status_code==200
    with api.Session() as s:
        assert PASSWORD not in str(s.get(User,'new-user').payload)
    assert client.post('/api/auth/logout',headers=headers).status_code==200
    assert client.get('/api/auth/me',headers=headers).status_code==401

def test_registration_quota_persists_after_duplicate_attempts(client,monkeypatch):
    monkeypatch.setenv('PUBLIC_REGISTRATION','true')
    for _ in range(5):
        assert client.post('/api/auth/register',json={'username':'admin','display_name':'Reserved','password':PASSWORD}).status_code==409
    r=client.post('/api/auth/register',json={'username':'fresh-user','display_name':'Fresh','password':PASSWORD})
    assert r.status_code==429 and int(r.headers['Retry-After'])>0

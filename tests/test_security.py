import pytest
from backend.security import hash_password,verify_password
from backend import api
from test_api import client,upload

PASSWORD='Synthetic-only-password-987'
def account(client,name='alice',role='requester'):
    response=client.post('/api/users',json={'username':name,'display_name':name.title(),'role':role,'password':PASSWORD})
    assert response.status_code==200,response.text
    return response.json()
def token(client,name):
    response=client.post('/api/auth/login',json={'username':name,'password':PASSWORD})
    assert response.status_code==200,response.text
    return {'Authorization':'Bearer '+response.json()['access_token']}

def test_salted_hashes_and_password_verification():
    a,b=hash_password(PASSWORD),hash_password(PASSWORD)
    assert a!=b and PASSWORD not in a
    assert verify_password(PASSWORD,a) and not verify_password('wrong',a)

def test_individual_login_logout_and_disable(client):
    account(client)
    headers=token(client,'alice')
    assert client.get('/api/auth/me',headers=headers).json()['id']=='alice'
    assert client.get('/api/auth/me',headers=headers).json()['role']=='requester'
    assert client.post('/api/auth/logout',headers=headers).json()['revoked']
    assert client.get('/api/auth/me',headers=headers).status_code==401
    headers=token(client,'alice')
    assert client.post('/api/users/alice/disable',json={'reason':'Account closed for synthetic test'}).status_code==200
    assert client.get('/api/auth/me',headers=headers).status_code==401
    assert client.post('/api/auth/login',json={'username':'alice','password':PASSWORD}).status_code==401
    assert 'password_hash' not in client.get('/api/users').text

def test_requester_ownership_for_lists_details_exports_and_replay(client):
    account(client); account(client,'bruno')
    alice,bruno=token(client,'alice'),token(client,'bruno')
    admin_headers=dict(client.headers)
    client.headers.update(alice)
    result=upload(client).json(); rid=result['id']; req=result['requirements'][0]['id']
    assert result['input'][0]['requester']=='alice'
    assert client.get('/api/runs').json()['total']==1
    client.headers.update(bruno)
    assert client.get('/api/runs').json()['total']==0
    assert client.get('/api/requirements').json()['total']==0
    assert client.get('/api/overview').json()['runs']==0
    for url in ['/api/runs/'+rid,'/api/runs/'+rid+'/export.csv',f'/api/requirements/{req}?run_id={rid}']:
        assert client.get(url).status_code==404
    assert client.post('/api/runs/'+rid+'/replay').status_code==404
    assert client.get('/api/purchase-orders').status_code==403
    client.headers.update(admin_headers)
    assert client.get('/api/runs/'+rid).status_code==200

def test_shared_db_throttle_and_no_password_echo(client):
    account(client)
    for _ in range(5): assert client.post('/api/auth/login',json={'username':'alice','password':'wrong'}).status_code==401
    assert client.post('/api/auth/login',json={'username':'alice','password':PASSWORD}).status_code==429
    response=client.post('/api/users',json={'username':'bruno','display_name':'Bruno','role':'requester','password':'short-secret'})
    assert response.status_code==422 and 'short-secret' not in response.text

def test_requester_cannot_create_accounts(client):
    account(client)
    response=client.post('/api/users',headers=token(client,'alice'),json={'username':'bruno','display_name':'Bruno','role':'admin','password':PASSWORD})
    assert response.status_code==403

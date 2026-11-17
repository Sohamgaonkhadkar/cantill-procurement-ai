from backend import security
import pytest
from fastapi import HTTPException
from test_api import client

def test_public_signup_and_legacy_sessions_cannot_unlock_hosted_assessment_masters(client,monkeypatch):
    monkeypatch.setenv('PUBLIC_REGISTRATION','true')
    password='Fictional-Registration-Test-2026!'
    public=client.post('/api/auth/register',json={'username':'public-signup','display_name':'Fictional self registrant','password':password})
    assert public.status_code==201,public.text
    provisioned=client.post('/api/users',json={'username':'private-provisioned','display_name':'Authorized assessment requester','password':password,'role':'requester'})
    assert provisioned.status_code==200,provisioned.text
    monkeypatch.setattr(security,'DEMO',False)
    monkeypatch.setattr(security,'isolated_demo',lambda:False)
    # Even a mistakenly enabled environment flag must fail closed in production.
    assert client.get('/api/auth/options').json()['registration_enabled'] is False
    denied=client.post('/api/auth/register',json={'username':'new-public-signup','display_name':'Fictional signup','password':password})
    assert denied.status_code==403
    headers={'Authorization':'Bearer '+public.json()['access_token']}
    assert client.get('/api/master-data',headers=headers).status_code==401
    assert client.post('/api/auth/login',json={'username':'public-signup','password':password}).status_code==401
    private=client.post('/api/auth/login',json={'username':'private-provisioned','password':password})
    assert private.status_code==200
    assert client.get('/api/master-data',headers={'Authorization':'Bearer '+private.json()['access_token']}).status_code==200
    monkeypatch.setattr(security,'isolated_demo',lambda:True)
    assert security.registration_enabled() is True
    with pytest.raises(HTTPException) as denied_admin:
        security.require_owner(security.Principal('admin','admin'))
    assert denied_admin.value.status_code==403

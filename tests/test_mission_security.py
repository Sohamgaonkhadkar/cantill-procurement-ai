import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event,current_thread
import pytest
from fastapi import HTTPException
from backend import api,security
from backend.db import AuthSession,Policy
from test_api import client,upload

PASSWORD='Synthetic-private-account-12345'

def test_production_never_publishes_or_accepts_legacy_privileged_aliases(client,monkeypatch):
    monkeypatch.setenv('SUBMISSION_ACCESS','true');monkeypatch.setenv('VERCEL','1')
    options=client.get('/api/auth/options').json()
    assert options['roles']==[] and not options['submission_access']
    for role in ['admin','buyer','requester']:
        assert client.post('/api/auth/login',json={'role':role,'password':f'corvo-{role}-demo'}).status_code==401

def test_evaluator_can_review_policy_but_cannot_administer_identities_or_import(client):
    r=client.post('/api/users',json={'username':'evaluator','display_name':'Private evaluator','role':'admin','password':PASSWORD,'access_scope':'evaluation'})
    assert r.status_code==200
    session=client.post('/api/auth/login',json={'username':'evaluator','password':PASSWORD}).json()
    headers={'Authorization':'Bearer '+session['access_token']}
    assert client.get('/api/auth/me',headers=headers).json()['access_scope']=='evaluation'
    assert client.get('/api/policies',headers=headers).status_code==200
    assert client.post('/api/policies/propose-amendment',headers=headers,json={'text':'Set spot limit to INR 75000','version':'scope-test','effective_date':'2026-04-01'}).status_code==200
    assert client.get('/api/users',headers=headers).status_code==403
    assert client.post('/api/users',headers=headers,json={'username':'escalated','display_name':'No escalation','role':'admin','password':PASSWORD}).status_code==403
    assert client.post('/api/users/admin/disable',headers=headers,json={'reason':'Forbidden privileged mutation'}).status_code==403
    assert client.post('/api/admin/import-data',headers=headers,files={'file':('source.zip',b'not a zip','application/zip')}).status_code==403

def test_same_input_has_distinct_ownership_without_changing_business_output(client):
    client.post('/api/users',json={'username':'alice','display_name':'Alice','role':'requester','password':PASSWORD})
    from conftest import line
    original=upload(client,[line(requester='alice')]).json()
    login=client.post('/api/auth/login',json={'username':'alice','password':PASSWORD}).json()
    client.headers['Authorization']='Bearer '+login['access_token']
    own=upload(client,[line(requester='alice')]).json()
    assert own['id']!=original['id'] and own['actor']=='alice'
    assert own['output_hash']==original['output_hash']
    assert client.get('/api/runs/'+own['id']).status_code==200
    assert client.get('/api/runs/'+original['id']).status_code==404

def test_expired_persisted_session_rejected(client):
    login=client.post('/api/auth/login',json={'role':'buyer','password':'corvo-demo'}).json()
    import base64,json
    sid=json.loads(base64.urlsafe_b64decode(login['access_token'].split('.')[0]))['sid']
    with api.Session.begin() as s:s.get(AuthSession,sid).expires_at=0
    assert client.get('/api/auth/me',headers={'Authorization':'Bearer '+login['access_token']}).status_code==401

def test_postgres_policy_edit_cannot_race_reviewed_approval(client,monkeypatch):
    if not os.getenv('TEST_DATABASE_URL'):pytest.skip('Requires dedicated PostgreSQL corvo_test database')
    r=client.post('/api/policies/propose-amendment',json={'text':'Set spot limit to INR 75000','version':'race-test','effective_date':'2026-04-01'}).json()
    assert client.post('/api/policies/race-test/review',json={'reason':'Reviewed the original threshold'}).status_code==200
    definition={k:r[k] for k in ['version','effective_date','parameters','rules']}
    definition['rules'][4]['when']['all'][0]['value']='999'
    locked=Event();release=Event();started=Event();finished=Event();original=api.get
    def get(s,model,key,lock=False):
        if model is Policy and key=='race-test' and current_thread().name.startswith('approve'):
            started.set()
        row=original(s,model,key,lock)
        if model is Policy and key=='race-test' and current_thread().name.startswith('edit'):
            locked.set();assert release.wait(10)
        return row
    monkeypatch.setattr(api,'get',get)
    def edit():return api.edit_policy('race-test',api.PolicyBody(policy=definition),actor='admin')
    def approve():
        try:return api.approve_policy('race-test',api.Note(reason='Concurrent attempted approval'),actor='admin')
        except HTTPException as exc:return exc.status_code
        finally:finished.set()
    with ThreadPoolExecutor(max_workers=1,thread_name_prefix='edit') as editor,ThreadPoolExecutor(max_workers=1,thread_name_prefix='approve') as approver:
        pending=editor.submit(edit);assert locked.wait(10)
        approval=approver.submit(approve);assert started.wait(10)
        try:assert not finished.wait(.3)
        finally:release.set()
        assert pending.result()['governance']['reviewed'] is False
        assert approval.result()==409
    with api.Session() as s:
        saved=s.get(Policy,'race-test')
        assert saved.status=='draft' and saved.payload['rules'][4]['when']['all'][0]['value']=='999'

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from threading import Barrier
import os
import pytest
from sqlalchemy import select,func
from backend import api
from backend.db import Run,Chat
from test_api import client


def ready(client,session_id=None,quantity=10):
    response=client.post('/api/chat/messages',json={'message':f'Need {quantity} bearing 6205-2RS at P-A by 2026-12-01 normal',**({'session_id':session_id} if session_id else {})})
    assert response.status_code==200,response.text
    assert response.json()['state']['ready']
    return response.json()['session_id']


def test_two_prs_in_one_conversation_have_distinct_commitments(client):
    sid=ready(client)
    first=client.post('/api/chat/messages',json={'session_id':sid,'message':'confirm'}).json()['run']
    ready(client,sid,20)
    second=client.post('/api/chat/messages',json={'session_id':sid,'message':'confirm'}).json()['run']
    assert first['input'][0]['pr_no']!=second['input'][0]['pr_no']
    for run in [first,second]:
        req=run['requirements'][0]
        response=client.post('/api/requirements/'+req['id']+'/approve',params={'run_id':run['id']},json={'reason':'Review independent synthetic chat submission'})
        assert response.status_code==200,response.text
    assert client.post('/api/chat/messages',json={'session_id':sid,'message':'confirm'}).json()['run'] is None
    with api.Session() as s: assert s.get(Chat,sid).payload['submission_count']==2


def test_independent_postgres_confirms_create_only_one_pr(client,monkeypatch):
    if not os.getenv('TEST_DATABASE_URL'): pytest.skip('Requires dedicated PostgreSQL corvo_test database')
    sid=ready(client); barrier=Barrier(2)
    # Bypass the process-local lock to exercise the cross-instance row lock.
    monkeypatch.setattr(api,'mutation_lock',nullcontext())
    def confirm(_):
        barrier.wait(timeout=10)
        return api.chat_message(api.ChatBody(session_id=sid,message='confirm'),'admin')
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(confirm,range(2)))
    assert sum(result['run'] is not None for result in results)==1
    with api.Session() as s:
        assert s.scalar(select(func.count()).select_from(Run))==1
        assert s.get(Chat,sid).payload['submission_count']==1

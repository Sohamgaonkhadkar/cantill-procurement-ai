import pytest
from sqlalchemy.exc import OperationalError,TimeoutError
from test_api import client,upload
from backend import api
from backend.domain import csv_bytes,INPUT_COLUMNS
from conftest import line

@pytest.mark.parametrize('error',[OperationalError('private database statement',{},Exception('private connection detail')),TimeoutError('private pool detail')])
def test_temporary_database_failure_is_retryable_without_fake_success(client,monkeypatch,error):
    session=api.Session
    def unavailable(*args,**kwargs):raise error
    monkeypatch.setattr(api,'Session',unavailable)
    response=upload(client)
    assert response.status_code==503 and response.headers['Retry-After']=='5'
    # Authentication reads persisted sessions first and reports HTTP_503 through
    # the standard HTTP exception envelope; it must not turn this into a 401.
    assert response.json()['error']['code']=='HTTP_503' and 'private' not in response.text
    monkeypatch.setattr(api,'Session',session)
    first=upload(client);second=upload(client)
    assert first.status_code==second.status_code==200 and first.json()['id']==second.json()['id']
    assert client.get('/api/runs').json()['total']==1

def test_batch_byte_limit_and_near_boundary_whole_batch_idempotency(client):
    raw=csv_bytes([line('BOUNDARY')],INPUT_COLUMNS)
    near=raw+b'\n'*(4_000_000-len(raw))
    first=client.post('/api/process-batch',files={'file':('boundary.csv',near,'text/csv')})
    assert first.status_code==200 and len(first.json()['rows'])==1
    duplicate=client.post('/api/process-batch',files={'file':('boundary.csv',raw,'text/csv')})
    assert duplicate.json()['id']==first.json()['id']
    rejected=client.post('/api/process-batch',files={'file':('oversize.csv',near+b'\n','text/csv')})
    assert rejected.status_code==413 and client.get('/api/runs').json()['total']==1

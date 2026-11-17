"""Independent invariants reject coherent-looking financial/evidence corruption."""
import json
from copy import deepcopy
import pytest
from backend.domain import csv_bytes,INPUT_COLUMNS
from scripts.validate_submission import validate
from scripts.submission_semantics import validate_snapshot,hash_value
from test_api import client,upload

def test_captured_run_and_private_master_support_independent_validation(client):
    run=upload(client).json();master=client.get('/api/runs/'+run['id']+'/master-snapshot')
    assert master.status_code==200
    result=validate_snapshot(run['input'],run['rows'],run,master.json())
    assert result['requirements_checked']==1 and result['master_records_checked']
    for defect in ['price','quantity','window','rank','ceiling']:
        bad=deepcopy(run)
        if defect=='price':bad['requirements'][0]['evidence']['valuation']['unit_price']='99'
        elif defect=='quantity':bad['requirements'][0]['quantity']='999'
        elif defect=='window':bad['requirements'][0]['lines'][0]['need_by_date']='2027-12-01'
        elif defect=='rank':bad['requirements'][0]['evidence']['ranking']=[]
        else:bad['data_hash']='altered'
        with pytest.raises(ValueError):validate_snapshot(bad['input'],bad['rows'],bad,master.json())

def test_private_snapshot_is_not_available_to_requester(client):
    run=upload(client).json()
    token=client.post('/api/auth/login',json={'role':'requester','password':'corvo-demo'}).json()['access_token']
    client.headers['Authorization']='Bearer '+token
    assert client.get('/api/runs/'+run['id']+'/master-snapshot').status_code==403

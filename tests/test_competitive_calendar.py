import csv,io
from copy import deepcopy
import pytest
from backend.policy import initial_policy
from backend.engine import select_policy
from backend.domain import INPUT_COLUMNS,csv_bytes
from test_api import client
from conftest import line

def checked(response):
    assert response.status_code==200,response.text
    return response.json()

def activate(client,version,effective='2026-11-15'):
    p=initial_policy();p['version']=version;p['effective_date']=effective
    p['rules'][4]['when']['all'][0]['value']='750'
    checked(client.post('/api/policies',json={'policy':p,'base_version':'5.0','source_text':'Reviewed synthetic limit change'}))
    for action in ['review','approve','activate']:checked(client.post(f'/api/policies/{version}/{action}',json={'reason':'Reviewed exact synthetic amendment conditions'}))

def test_mixed_date_run2_calendar_pinned_history_and_replay(client):
    activate(client,'6.0')
    rows=[line('BEFORE',created_at='2026-11-14 10:00'),line('ON',created_at='2026-11-15 10:00'),line('AFTER',created_at='2026-11-16 10:00')]
    raw=csv_bytes(rows,INPUT_COLUMNS)
    def run(**fields):return checked(client.post('/api/process-batch',files={'file':('mixed.csv',raw,'text/csv')},data=fields))
    automatic=run();history=run(policy_version='5.0');calendar=run(policy_version='6.0',policy_mode='calendar');pinned=run(policy_version='6.0')
    expected={'BEFORE':('5.0','SPOT_PO'),'ON':('6.0','RFQ'),'AFTER':('6.0','RFQ')}
    for result in [automatic,calendar]:
        assert {r['pr_no']:(r['policy_version'],r['route']) for r in result['rows']}==expected
        assert len(result['requirements'])==2
        values={r['pr_no']:r for r in result['rows']}
        assert values['BEFORE']['group_id']!=values['ON']['group_id']==values['AFTER']['group_id']
    assert {r['policy_version'] for r in history['rows']}=={'5.0'} and len(history['requirements'])==1
    assert next(r for r in pinned['rows'] if r['pr_no']=='BEFORE')['route']=='NOT_PROCESSED'
    assert calendar['calendar_version']=='6.0' and calendar['explicit_policy'] is None
    assert calendar['input_hash']==history['input_hash']
    for result in [automatic,history,calendar,pinned]:
        assert checked(client.post('/api/runs/'+result['id']+'/replay'))['matches']
        export=client.get('/api/runs/'+result['id']+'/export.csv')
        assert list(csv.DictReader(io.StringIO(export.text)))==result['rows']

def test_equal_effective_dates_use_authorized_supersession_not_version_name(client):
    for version in ['5.9','5.10','6.0','NOV-2026-AMENDMENT']:
        activate(client,version)
        active=[p for p in checked(client.get('/api/policies'))['items'] if p['status']=='active' and p['effective_date']=='2026-11-15']
        assert [p['version'] for p in active]==[version]
    with pytest.raises(ValueError,match='Conflicting effective'):
        from datetime import date
        a=initial_policy();b=deepcopy(a);b['version']='5.10'
        select_policy([a,b],date(2026,11,19))

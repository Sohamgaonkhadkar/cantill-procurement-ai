"""Full frozen-application synthetic rehearsal with literal business expectations."""
import json,csv,io,time
from copy import deepcopy
from pathlib import Path
from backend.domain import INPUT_COLUMNS,csv_bytes
from scripts.validate_submission import validate
from scripts.submission_semantics import hash_value
from test_api import client
from conftest import line,contract

def ok(response):
    assert response.status_code==200,response.text
    return response.json()

def test_five_instruction_mixed_calendar_rehearsal(client,tmp_path):
    started=time.monotonic()
    rows=[line('BEFORE',created_at='2026-11-14 10:00',quantity='8'),line('AFTER',created_at='2026-11-15 10:00',quantity='8'),line('OTHER',created_at='2026-11-15 10:00',quantity='8',plant='P-B'),line('EMERGENCY',created_at='2026-11-15 10:00',quantity='8',urgency='Emergency',need_by_date='2026-12-20'),line('HOSE',created_at='2026-11-15 10:00',item_code='I-B',description='Hydraulic hose 1/2 inch 2 wire',uom='MTR',quantity='4'),line('CAPEX',created_at='2026-11-15 10:00',item_code='I-C',uom='NOS',quantity='1'),line('NEW',created_at='2026-11-15 10:00',item_code='',description='Custom fictional optical monitor',quantity='2',estimated_unit_price='123'),line('INVALID',quantity='0')]
    raw=csv_bytes(rows,INPUT_COLUMNS)
    def run(version,mode='pinned'):return ok(client.post('/api/process-batch',files={'file':('novel.csv',raw,'text/csv')},data={'policy_version':version,'policy_mode':mode}))
    before=run('5.0')
    source='''Change the spot purchasing limit from INR 200000 to INR 175000.
Set grouping window to twelve calendar days.
Set quality ranking weight to 22.
At plant Alpha plant, require RFQ for Bearings purchases above INR 700 except emergency.
For Hydraulics requests at P-A with value between INR 700 and INR 900 inclusive, require RFP.
Apply policy from 15 November 2026.'''
    draft=ok(client.post('/api/policies/upload-amendment',files={'file':('novel.txt',source,'text/plain')},data={'version':'REHEARSAL-CALENDAR','effective_date':'2026-11-15','base_version':'5.0'}))
    assert len(draft['interpretation']['source_clauses'])==6 and len(draft['interpretation']['unresolved_clauses'])==1
    definition={k:deepcopy(draft[k]) for k in ['version','effective_date','parameters','rules']}
    definition['rules'].append({'id':'manual-hose-range','priority':2,'route':'RFP','reason':'Reviewed exact inclusive Hydraulics interval','when':{'all':[{'fact':'requirement.plant','op':'eq','value':'P-A'},{'fact':'item.category','op':'eq','value':'Hydraulics'},{'fact':'requirement.group_value_inr','op':'gte','value':'700'},{'fact':'requirement.group_value_inr','op':'lte','value':'900'}]}})
    ok(client.put('/api/policies/REHEARSAL-CALENDAR',json={'policy':definition,'base_version':'5.0','source_text':source}))
    sim=ok(client.post('/api/policies/REHEARSAL-CALENDAR/simulate',json={'run_id':before['id'],'policy_mode':'calendar'}))
    evidence={'clause_id':draft['interpretation']['unresolved_clauses'][0]['id'],'meaning':'Hydraulics inclusive interval produces RFP','scope':'Hydraulics at P-A, inclusive 700 through 900','paths':['rules[manual-hose-range]'],'priority':2,'effective_date':'2026-11-15','evidence':'Checked exact source plant/category and both inclusive boundaries','confirmed':True}
    ok(client.post('/api/policies/REHEARSAL-CALENDAR/review',json={'reason':'Reviewed each clause, simulation and protected-route precedence','manual_verification':True,'precedence_acknowledged':True,'reconciliations':[evidence]}))
    for action in ['approve','activate']:ok(client.post('/api/policies/REHEARSAL-CALENDAR/'+action,json={'reason':'Verified source and independent scenario expectations'}))
    after=run('REHEARSAL-CALENDAR','calendar')
    expected_before={'BEFORE':('SPOT_PO','1600.00'),'AFTER':('SPOT_PO','1600.00'),'OTHER':('SPOT_PO','800.00'),'EMERGENCY':('EMERGENCY_PO','800.00'),'HOSE':('RFQ','800.00'),'CAPEX':('CAPEX_SOURCING','1000000.00'),'NEW':('NEW_ITEM_SOURCING','246.00'),'INVALID':('NOT_PROCESSED','')}
    expected_after={**expected_before,'BEFORE':('SPOT_PO','800.00'),'AFTER':('RFQ','800.00'),'HOSE':('RFP','800.00')}
    for run_,expected in [(before,expected_before),(after,expected_after)]:
        assert {r['pr_no']:(r['route'],r['group_value_inr']) for r in run_['rows']}==expected
        assert ok(client.post('/api/runs/'+run_['id']+'/replay'))['matches']
    assert sim['result']['rows']==after['rows'] and before['input_hash']==after['input_hash']
    master=ok(client.get('/api/runs/'+after['id']+'/master-snapshot'))
    # Each CSV field is checked against the captured JSON; independent invariants
    # then recalculate quantities, values, source prices, dates, ranks and windows.
    (tmp_path/'input.csv').write_bytes(raw)
    for name,r in [('run1',before),('run2',after)]:
        response=client.get('/api/runs/'+r['id']+'/export.csv');assert response.status_code==200
        (tmp_path/(name+'.csv')).write_bytes(response.content)
        (tmp_path/(name+'.json')).write_text(json.dumps(r),encoding='utf-8')
    response=client.get('/api/preferred-suppliers/export.csv',params={'as_of':'2026-11-19','policy_version':'REHEARSAL-CALENDAR'});assert response.status_code==200
    (tmp_path/'preferred.csv').write_bytes(response.content)
    (tmp_path/'masters.json').write_text(json.dumps(master),encoding='utf-8')
    (tmp_path/'preferred.json').write_text(json.dumps({'as_of':'2026-11-19','policy_version':'REHEARSAL-CALENDAR'}),encoding='utf-8')
    report=validate(tmp_path/'input.csv',tmp_path/'run1.csv',tmp_path/'run2.csv',tmp_path/'preferred.csv','REHEARSAL-CALENDAR',run1_snapshot=tmp_path/'run1.json',run2_snapshot=tmp_path/'run2.json',masters_snapshot=tmp_path/'masters.json',preferred_metadata=tmp_path/'preferred.json')
    assert report['valid'] and not report['warnings']
    assert client.get('/api/purchase-orders').json()['total']==0
    report.update(seconds=round(time.monotonic()-started,2),affected_lines=ok(client.get('/api/runs/'+before['id']+'/compare/'+after['id']))['affected_lines'],invalid_lines=len(after['issues']),supplier_eligibility_failures=0,source_clauses=6)
    (tmp_path/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

def test_equal_rate_contract_tie_and_all_thirteen_csv_fields(data,policy):
    import hashlib
    from backend.engine import process
    # IDs independently follow the documented SHA-256 encoding; no engine helper.
    def key(value):return hashlib.sha256(json.dumps(value,separators=(',',':')).encode()).hexdigest()[:12].upper()
    data.contracts=[contract('ZZZ',supplier_id='S-B'),contract('AAA',supplier_id='S-A')]
    result=process([line()],data,[policy]);group='REQ-'+key(['PR-A','1']);po='PO-'+key([group,'S-A','P-A','CONTRACT_PO'])
    assert result['rows']==[{'pr_no':'PR-A','pr_line':'1','resolved_item_code':'I-A','group_id':group,'po_id':po,'decision':'PO','route':'CONTRACT_PO','supplier_id':'S-A','unit_price':'90.00','group_value_inr':'900.00','suggested_supplier_ids':'','policy_version':'5.0','reason':'Policy 5.0 clause 5.2: Eligible contract with sufficient ceiling. Valuation contract AAA. Order price evidence AAA.'}]

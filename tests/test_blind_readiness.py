"""Fresh synthetic blind-test rehearsals with literal, independent expectations."""
from copy import deepcopy
import csv,hashlib,io
from backend.domain import INPUT_COLUMNS,csv_bytes
from scripts.validate_submission import validate
from test_api import client
from conftest import line

HEADERS=['pr_no','pr_line','resolved_item_code','group_id','po_id','decision','route','supplier_id','unit_price','group_value_inr','suggested_supplier_ids','policy_version','reason']

def ok(response):
    assert response.status_code==200,response.text
    return response.json()

def upload_policy(client,source,version):
    return ok(client.post('/api/policies/upload-amendment',files={'file':('new-amendment.txt',source.encode(),'text/plain')},data={'base_version':'5.0','version':version,'effective_date':'2026-11-01'}))

def process(client,batch,version):
    return ok(client.post('/api/process-batch',files={'file':('synthetic.csv',batch,'text/csv')},data={'policy_version':version}))

def activate(client,version,manual=False):
    for action in ['review','approve','activate']:
        ok(client.post(f'/api/policies/{version}/{action}',json={'reason':'Independently checked source clauses, scope and precedence','manual_verification':manual} if action=='review' else {'reason':'Independently checked source clauses, scope and precedence'}))

def test_nine_clause_two_run_rehearsal_and_three_exports(client,tmp_path):
    source='''Do not change the emergency limit.
At plant Alpha plant, require RFQ for Bearings purchases at least INR 750 except urgency is emergency.
Set grouping window to eleven calendar days.
Set delivery ranking weight to 30.
Set quality ranking weight to 25.
Exclude supplier S-B from all purchasing recommendations.
Do not use contracts from supplier S-A.
Apply policy from 1 November 2026.
Suggest 2 suppliers for RFQ.'''
    rows=[line('AUDIT-A',quantity='7.5'),line('AUDIT-B',plant='P-B',quantity='7.5'),
          line('AUDIT-C',quantity='20',urgency='Emergency',need_by_date='2026-12-05'),
          line('AUDIT-D',quantity='7.4999',need_by_date='2026-12-20',description='Synthetic, quoted "bearing"\nsecond line')]
    batch=csv_bytes(rows,INPUT_COLUMNS);before=process(client,batch,'5.0')
    original=next(p for p in ok(client.get('/api/policies'))['items'] if p['version']=='5.0')
    draft=upload_policy(client,source,'AUDIT-NINE')
    assert draft['interpretation']['complete'] and len(draft['interpretation']['source_clauses'])==9
    assert draft['governance']['source_text']==source==draft['governance']['original_source_text']
    assert draft['governance']['source_bytes_hash']==hashlib.sha256(source.encode()).hexdigest()
    assert draft['effective_date']=='2026-11-01' and draft['parameters']['group_days']==11
    assert draft['rules'][:-1]==original['rules']
    assert draft['parameters']['history_days']==original['parameters']['history_days']
    assert draft['parameters']['weights']['frequency']==original['parameters']['weights']['frequency']
    simulation=ok(client.post('/api/policies/AUDIT-NINE/simulate',json={'run_id':before['id']}))
    assert simulation['comparison']['affected_lines']>0
    activate(client,'AUDIT-NINE');after=process(client,batch,'AUDIT-NINE')
    first={r['pr_no']:r for r in before['rows']};second={r['pr_no']:r for r in after['rows']}
    assert {key:r['route'] for key,r in first.items()}=={'AUDIT-A':'SPOT_PO','AUDIT-B':'SPOT_PO','AUDIT-C':'EMERGENCY_PO','AUDIT-D':'SPOT_PO'}
    assert {key:r['route'] for key,r in second.items()}=={'AUDIT-A':'RFQ','AUDIT-B':'SPOT_PO','AUDIT-C':'EMERGENCY_PO','AUDIT-D':'SPOT_PO'}
    assert second['AUDIT-A']['group_value_inr']=='750.00' and second['AUDIT-D']['group_value_inr']=='749.99'
    assert second['AUDIT-A']['suggested_supplier_ids']=='S-A'
    assert before['input_hash']==after['input_hash']
    assert process(client,batch,'5.0')['output_hash']==before['output_hash']
    for run in [before,after]:assert ok(client.post('/api/runs/'+run['id']+'/replay'))['matches']
    paths=[]
    for name,run in [('run1.csv',before),('run2.csv',after)]:
        response=client.get('/api/runs/'+run['id']+'/export.csv');assert response.status_code==200
        assert list(csv.reader(io.StringIO(response.text)))[0]==HEADERS
        assert len(list(csv.DictReader(io.StringIO(response.text))))==4
        path=tmp_path/name;path.write_bytes(response.content);paths.append(path)
    preferred=client.get('/api/preferred-suppliers/export.csv',params={'as_of':'2026-11-19','policy_version':'AUDIT-NINE'})
    assert preferred.status_code==200
    assert list(csv.DictReader(io.StringIO(preferred.text)))==[{'item_code':'I-A','rank':'1','supplier_id':'S-A','reference_price':'100.00'}]
    preferred_path=tmp_path/'preferred.csv';preferred_path.write_bytes(preferred.content)
    input_path=tmp_path/'input.csv';input_path.write_bytes(batch)
    validate(input_path,*paths,preferred_path,'AUDIT-NINE')
    # A 12-day gap groups under v5.0 but not the amended 11-day window.
    gap=csv_bytes([line('GAP-A',plant='P-B'),line('GAP-B',plant='P-B',created_at='2026-11-13 10:00')],INPUT_COLUMNS)
    assert len(process(client,gap,'5.0')['requirements'])==1
    assert len(process(client,gap,'AUDIT-NINE')['requirements'])==2

def test_unfamiliar_representable_clause_requires_real_structured_reconciliation(client):
    source='For normal Bearings requests at P-A, use RFQ when value is between INR 700 and INR 900 inclusive.'
    draft=upload_policy(client,source,'AUDIT-MANUAL')
    assert not draft['interpretation']['complete'] and len(draft['interpretation']['unresolved_clauses'])==1
    for action in ['review','approve','activate']:
        assert client.post('/api/policies/AUDIT-MANUAL/'+action,json={'reason':'A checkbox cannot implement an unknown clause','manual_verification':True} if action=='review' else {'reason':'Must not bypass review'}).status_code==409
    definition={key:deepcopy(draft[key]) for key in ['version','effective_date','parameters','rules']}
    definition['rules'].append({'id':'inclusive-normal-range','priority':5,'route':'RFQ','reason':'Reviewed exact normal Bearings interval at plant P-A','when':{'all':[
        {'fact':'requirement.plant','op':'eq','value':'P-A'},
        {'fact':'item.category','op':'eq','value':'Bearings'},
        {'not':{'fact':'requirement.is_emergency','op':'eq','value':True}},
        {'fact':'requirement.group_value_inr','op':'gte','value':'700'},
        {'fact':'requirement.group_value_inr','op':'lte','value':'900'}]}})
    saved=ok(client.put('/api/policies/AUDIT-MANUAL',json={'policy':definition,'base_version':'5.0','source_text':source}))
    assert saved['governance']['manual_reconciled'] and saved['governance']['original_source_text']==source
    activate(client,'AUDIT-MANUAL',manual=True)
    for quantity,plant,urgency,route in [('7','P-A','Normal','RFQ'),('9','P-A','Normal','RFQ'),('9.0001','P-A','Normal','SPOT_PO'),('8','P-B','Normal','SPOT_PO'),('8','P-A','Emergency','EMERGENCY_PO')]:
        run=process(client,csv_bytes([line(quantity=quantity,plant=plant,urgency=urgency)],INPUT_COLUMNS),'AUDIT-MANUAL')
        assert run['rows'][0]['route']==route

def test_priority_collision_is_classified_as_conflict_and_cannot_activate(client):
    source='If plant P-A and value above INR 700 require RFQ (priority 10)'
    draft=upload_policy(client,source,'AUDIT-PRIORITY')
    assert not draft['interpretation']['complete']
    assert draft['interpretation']['conflicts']
    assert draft['interpretation']['source_clauses'][0]['status']=='conflict'
    assert client.post('/api/policies/AUDIT-PRIORITY/review',json={'reason':'Cannot accept colliding priority'}).status_code==409

def test_future_amendment_preserves_historical_policy_and_changed_limits(client):
    draft=upload_policy(client,'Set spot limit to INR 750\nApply policy from 15 November 2026','AUDIT-DATED')
    assert draft['effective_date']=='2026-11-15'
    activate(client,'AUDIT-DATED')
    batch=csv_bytes([line('EARLIER',created_at='2026-11-14 10:00'),line('LATER',created_at='2026-11-15 10:00')],INPUT_COLUMNS)
    automatic=ok(client.post('/api/process-batch',files={'file':('dated.csv',batch,'text/csv')}))
    expected={r['pr_no']:(r['policy_version'],r['route']) for r in automatic['rows']}
    assert expected=={'EARLIER':('5.0','SPOT_PO'),'LATER':('AUDIT-DATED','RFQ')}
    assert len(automatic['requirements'])==2

from copy import deepcopy
import pytest
from backend.precedence import analyze,witness
from test_api import client

def ok(response):
    assert response.status_code==200,response.text
    return response.json()

def scoped(rule_id,category,plant,low,high,priority,route='RFQ'):
    return {'id':rule_id,'priority':priority,'route':route,'reason':'Reviewed bounded source instruction','when':{'all':[
        {'fact':'item.category','op':'eq','value':category},{'fact':'requirement.plant','op':'eq','value':plant},
        {'fact':'requirement.is_emergency','op':'eq','value':False},
        {'fact':'requirement.group_value_inr','op':'gte','value':low},{'fact':'requirement.group_value_inr','op':'lte','value':high}]}}

def test_precedence_reports_protected_routes_and_excludes_disjoint_scopes(policy):
    p=deepcopy(policy);p['rules'].append(scoped('normal-bearings','Bearings','P-A','75000','150000',5))
    report=analyze(policy,p)
    assert report['requires_acknowledgement'] and report['complete']
    assert any(w['later_route']=='CONTRACT_PO' for w in report['warnings'])
    assert not any(w['later_route']=='EMERGENCY_PO' for w in report['warnings'])
    assert witness(p['rules'][-1]['when'],{'fact':'requirement.plant','op':'eq','value':'P-B'}) is False
    assert witness(p['rules'][-1]['when'],{'fact':'item.category','op':'eq','value':'Hydraulics'}) is False
    p['rules'][-1]['when']['all'].append({'fact':'item.item_type','op':'ne','value':'Capex'})
    assert not any(w['later_route']=='CAPEX_SOURCING' for w in analyze(policy,p)['warnings'])

def setup_unresolved(client):
    source='''For normal Bearings requests at P-A with value between INR 700 and INR 900 inclusive, mandate RFQ.
For normal Hydraulics requests at P-B with value between INR 400 and INR 600 inclusive, mandate RFP.
For normal Capital requests at P-A with value between INR 1000000 and INR 2000000 inclusive, mandate RFQ.'''
    draft=ok(client.post('/api/policies/upload-amendment',files={'file':('unfamiliar.txt',source,'text/plain')},data={'version':'RECONCILE-6','effective_date':'2026-11-01','base_version':'5.0'}))
    assert len(draft['interpretation']['unresolved_clauses'])==3
    definition={k:deepcopy(draft[k]) for k in ['version','effective_date','parameters','rules']}
    rules=[scoped('range-one','Bearings','P-A','700','900',5),scoped('range-two','Hydraulics','P-B','400','600',6,'RFP'),scoped('range-three','Capital','P-A','1000000','2000000',7)]
    mappings=[{'clause_id':entry['id'],'meaning':'Implement the inclusive value interval and resulting route','scope':rule['when']['all'][0]['value']+' at '+rule['when']['all'][1]['value'],'paths':['rules['+rule['id']+']'],'priority':rule['priority'],'effective_date':'2026-11-01','evidence':'Checked both inclusive boundaries, plant, category and normal-only conditions','confirmed':True} for entry,rule in zip(draft['interpretation']['unresolved_clauses'],rules)]
    return source,definition,rules,mappings

def test_three_unresolved_clauses_cannot_be_reconciled_by_one_mapping_or_unrelated_edit(client):
    source,definition,rules,mappings=setup_unresolved(client)
    definition['parameters']['weights']['quality']=22
    ok(client.put('/api/policies/RECONCILE-6',json={'policy':definition,'base_version':'5.0','source_text':source}))
    body={'reason':'Explicit review of every unresolved source instruction','manual_verification':True,'precedence_acknowledged':True,'reconciliations':mappings[:1]}
    assert client.post('/api/policies/RECONCILE-6/review',json=body).status_code==409
    body['reconciliations']=[dict(m,paths=['parameters.weights.quality']) for m in mappings]
    response=client.post('/api/policies/RECONCILE-6/review',json=body)
    assert response.status_code==409 and 'unrelated' in response.text
    definition['rules']+=rules
    saved=ok(client.put('/api/policies/RECONCILE-6',json={'policy':definition,'base_version':'5.0','source_text':source}))
    assert saved['governance']['structured_changes_saved'] and not saved['governance']['manual_reconciled']
    body['reconciliations']=mappings
    body['precedence_acknowledged']=False
    assert client.post('/api/policies/RECONCILE-6/review',json=body).status_code==409
    body['precedence_acknowledged']=True
    reviewed=ok(client.post('/api/policies/RECONCILE-6/review',json=body))
    assert reviewed['governance']['manual_reconciled'] and len(reviewed['governance']['clause_reconciliations'])==3
    for action in ['approve','activate']:ok(client.post('/api/policies/RECONCILE-6/'+action,json={'reason':'All source mappings and priority overlaps independently checked'}))

@pytest.mark.parametrize('damage',['scope','amount','priority','date','confirmation','scope_operator','broad_scope','reversed_interval','strict_interval'])
def test_false_clause_evidence_is_rejected(client,damage):
    source,definition,rules,mappings=setup_unresolved(client)
    if damage=='scope':rules[0]['when']['all'][1]['value']='P-B'
    if damage=='amount':rules[0]['when']['all'][3]['value']='701'
    if damage=='priority':mappings[0]['priority']=99
    if damage=='date':mappings[0]['effective_date']='2027-01-01'
    if damage=='confirmation':mappings[0]['confirmed']=False
    if damage=='scope_operator':rules[0]['when']['all'][1]['op']='ne'
    if damage=='broad_scope':rules[0]['when']={'any':[rules[0]['when'],{'fact':'requirement.group_value_inr','op':'gte','value':'700'}]}
    if damage=='reversed_interval':rules[0]['when']['all'][3]['value']='900';rules[0]['when']['all'][4]['value']='700'
    if damage=='strict_interval':rules[0]['when']['all'][3]['op']='gt'
    definition['rules']+=rules
    ok(client.put('/api/policies/RECONCILE-6',json={'policy':definition,'base_version':'5.0','source_text':source}))
    assert client.post('/api/policies/RECONCILE-6/review',json={'reason':'Check source evidence cannot silently drift','manual_verification':True,'precedence_acknowledged':True,'reconciliations':mappings}).status_code==409

def test_date_only_manual_correction_is_executable_and_bound_to_the_source(client):
    source='Commencement date shall be 2026-11-15.'
    draft=ok(client.post('/api/policies/propose-amendment',json={'text':source,'version':'DATE-ONLY','effective_date':'2026-11-01'}))
    assert len(draft['interpretation']['unresolved_clauses'])==1
    definition={key:deepcopy(draft[key]) for key in ['version','effective_date','parameters','rules']}
    mapping={'clause_id':draft['interpretation']['unresolved_clauses'][0]['id'],'meaning':'The amended policy starts on the stated commencement date','scope':'All requests governed by this version','paths':['effective_date'],'effective_date':'2026-11-16','evidence':'Checked the policy commencement date against the original clause','confirmed':True}
    definition['effective_date']='2026-11-16'
    saved=ok(client.put('/api/policies/DATE-ONLY',json={'policy':definition,'base_version':'5.0','source_text':source}))
    assert saved['governance']['structured_changes_saved']
    body={'reason':'Verify exact policy commencement date','manual_verification':True,'reconciliations':[mapping]}
    assert client.post('/api/policies/DATE-ONLY/review',json=body).status_code==409
    definition['effective_date']='2026-11-15';mapping['effective_date']='2026-11-15'
    ok(client.put('/api/policies/DATE-ONLY',json={'policy':definition,'base_version':'5.0','source_text':source}))
    reviewed=ok(client.post('/api/policies/DATE-ONLY/review',json=body))
    assert reviewed['governance']['manual_reconciled']
    ok(client.post('/api/policies/DATE-ONLY/approve',json={'reason':'Verified reviewed definition including effective date'}))

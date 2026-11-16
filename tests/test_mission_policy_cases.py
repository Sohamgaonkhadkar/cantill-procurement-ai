from copy import deepcopy
from datetime import date
import pytest
from backend.language import interpret
from backend.engine import process
from backend.suppliers import preferred
from backend.policy import validate_policy
from conftest import line,contract
from test_api import client,upload

def proposal(policy,data,text):
    result=interpret(policy,text,'6.0','2026-04-01',data)
    assert result['complete'],result['unresolved_clauses']
    return result['policy']

def test_requested_eight_amendments_have_precise_effects(data,policy):
    original=deepcopy(policy)
    changed=proposal(policy,data,'Increase the spot-purchase threshold to INR 75,000.')
    assert changed['rules'][4]['when']['all'][0]['value']=='75000'
    assert changed['rules'][:4]==policy['rules'][:4] and changed['rules'][5:]==policy['rules'][5:]
    scoped=proposal(policy,data,'At plant P-A, require RFQ for bearing purchases above INR 50,000.')
    assert process([line(quantity='501')],data,[scoped])['rows'][0]['route']=='RFQ'
    assert process([line(quantity='501',plant='P-B')],data,[scoped])['rows'][0]['route']=='SPOT_PO'
    assert proposal(policy,data,'Do not change the emergency purchasing threshold.')['rules']==policy['rules']
    assert proposal(policy,data,'Exclude inactive suppliers from all purchasing recommendations.')['rules']==policy['rules']
    assert proposal(policy,data,'Increase the preferred supplier count for RFQ from three to five.')['parameters']['suggestions']['RFQ']==5
    extra=proposal(policy,data,'For capital equipment, require an additional sourcing approval.')
    assert process([line(item_code='I-C')],data,[extra])['requirements'][0]['required_approvals']==2
    assert proposal(policy,data,'Change the grouping window to ten calendar days.')['parameters']['group_days']==10
    dated=proposal(policy,data,'If plant P-A require RFQ\nApply the new rule only from 1 January 2027.')
    assert process([line()],data,[dated])['rows'][0]['route']=='SPOT_PO'
    assert process([line(created_at='2027-01-01 10:00',need_by_date='2027-01-20')],data,[dated])['rows'][0]['route']=='RFQ'
    assert policy==original

@pytest.mark.parametrize('text',[
    'Set spot limit to INR 75000\nSet spot limit to INR 80000',
    'Do not change the emergency purchasing threshold\nSet emergency limit to INR 75000',
    'Set emergency limit to INR 75000\nDo not change the emergency purchasing threshold',
    'If plant P-A require RFQ\nIf plant P-A require RFP',
])
def test_conflicting_instructions_remain_unresolved(data,policy,text):
    result=interpret(policy,text,'6.0','2026-04-01',data)
    assert not result['complete'] and result['conflicts'] and result['unresolved_clauses']
    assert any(clause['status']=='conflict' for clause in result['source_clauses'])

def test_exclusion_negation_and_future_policy_date(data,policy):
    changed=proposal(policy,data,'If plant P-A except emergency require RFP')
    assert process([line()],data,[changed])['rows'][0]['route']=='RFP'
    assert process([line(urgency='Emergency')],data,[changed])['rows'][0]['route']=='EMERGENCY_PO'
    future=proposal(policy,data,'Set spot limit to INR 75000\nApply the policy only from 1 January 2027')
    assert future['effective_date']=='2027-01-01'
    assert process([line()],data,[policy,future])['rows'][0]['policy_version']=='5.0'

def test_supplier_and_contract_restrictions_cannot_be_undone_by_ranking(data,policy):
    data.contracts=[contract()]
    changed=proposal(policy,data,'Exclude supplier S-A from all purchasing recommendations\nSet delivery ranking weight to 100')
    result=process([line()],data,[changed])
    assert result['rows'][0]['supplier_id'] not in {'S-A','S-X'}
    assert 'S-A' not in result['rows'][0]['suggested_supplier_ids'] and 'S-X' not in result['rows'][0]['suggested_supplier_ids']
    assert preferred(data,'I-A',date(2026,11,1),changed)==[]
    changed=proposal(policy,data,'Exclude contracts from supplier S-A')
    result=process([line()],data,[changed])
    assert result['rows'][0]['route']=='SPOT_PO' and result['rows'][0]['unit_price']=='100.00'
    assert result['requirements'][0]['evidence']['contracts'][0]['rejection']=='Contract supplier excluded by policy'

def test_complete_multiclause_document_preserves_unrelated_fields(data,policy):
    changed=proposal(policy,data,'Set spot limit to INR 75000. Do not change the emergency purchasing threshold.\nSet grouping window to ten calendar days\nSet quality ranking weight to 30\nSuggest 5 suppliers for RFQ')
    assert changed['parameters']['weights']=={**policy['parameters']['weights'],'quality':30}
    assert changed['parameters']['need_days']==policy['parameters']['need_days']
    assert changed['rules'][3]==policy['rules'][3]
    assert changed['parameters']['suggestions']['RFP']==5

def test_manual_checkbox_is_insufficient_but_saved_structured_correction_can_be_reviewed(client):
    text='All bearing purchases at the Alpha plant must request quotations.'
    p=client.post('/api/policies/propose-amendment',json={'text':text,'version':'manual-corrected','effective_date':'2026-04-01'}).json()
    assert p['interpretation']['unresolved_clauses']
    note={'reason':'Verified manual mapping of Alpha to P-A and bearings to RFQ','manual_verification':True}
    assert client.post('/api/policies/manual-corrected/review',json=note).status_code==409
    definition={k:p[k] for k in ['version','effective_date','parameters','rules']}
    definition['rules'].append({'id':'manual-plant-bearing','priority':5,'when':{'all':[{'fact':'requirement.plant','op':'eq','value':'P-A'},{'fact':'item.category','op':'eq','value':'Bearings'}]},'route':'RFQ','reason':'Human reconciled the explicit plant/category clause'})
    edited=client.put('/api/policies/manual-corrected',json={'policy':definition,'base_version':'5.0','source_text':text})
    assert edited.status_code==200 and edited.json()['governance']['manual_reconciled']
    assert client.post('/api/policies/manual-corrected/review',json=note).status_code==200
    for action in ['approve','activate']:assert client.post('/api/policies/manual-corrected/'+action,json={'reason':'Verified source and structured correction'}).status_code==200
    assert upload(client,version='manual-corrected').json()['rows'][0]['route']=='RFQ'

def test_stale_policy_cannot_be_approved_after_effective_amendment(client):
    before=upload(client).json()
    client.post('/api/policies/propose-amendment',json={'text':'Set spot limit to INR 500','version':'retroactive','effective_date':'2026-04-01'})
    for action in ['review','approve','activate']:assert client.post('/api/policies/retroactive/'+action,json={'reason':'Explicit reviewed effective amendment'}).status_code==200
    req=before['requirements'][0]['id']
    response=client.post('/api/requirements/'+req+'/approve',params={'run_id':before['id']},json={'reason':'Attempt stale purchasing recommendation'})
    assert response.status_code==409 and 'newer effective policy' in response.text
    assert client.get('/api/purchase-orders').json()['total']==0

def test_capex_additional_approval_requires_distinct_accounts_before_action(client):
    client.post('/api/policies/propose-amendment',json={'text':'For capital equipment, require an additional sourcing approval','version':'dual-capex','effective_date':'2026-04-01'})
    for action in ['review','approve','activate']:assert client.post('/api/policies/dual-capex/'+action,json={'reason':'Source explicitly requires a second sourcing approval'}).status_code==200
    run=upload(client,[line(item_code='I-C')],version='dual-capex').json();req=run['requirements'][0]
    assert req['required_approvals']==2
    url='/api/requirements/'+req['id']+'/approve';params={'run_id':run['id']};note={'reason':'First verified capex sourcing reviewer'}
    first=client.post(url,params=params,json=note)
    assert first.status_code==200 and first.json()['status']=='awaiting_approval'
    assert client.get('/api/sourcing').json()['total']==0
    assert client.post(url,params=params,json=note).status_code==409
    assert client.post('/api/requirements/'+req['id']+'/override',params=params,json={'route':'RFQ','reason':'Attempt to bypass the additional approval'}).status_code==409
    session=client.post('/api/auth/login',json={'role':'buyer','password':'corvo-demo'}).json()
    second=client.post(url,params=params,json={'reason':'Distinct second reviewer confirmed scope'},headers={'Authorization':'Bearer '+session['access_token']})
    assert second.status_code==200 and second.json()['status']=='approved'
    assert client.get('/api/sourcing').json()['total']==1
    assert len(second.json()['recommendations'][0]['approval_votes'])==2

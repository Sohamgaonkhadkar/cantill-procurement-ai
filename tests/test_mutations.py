from copy import deepcopy
import pytest
from backend.engine import process
from backend.policy import condition,validate_policy
from backend.chat import parse_message
from conftest import line,contract

@pytest.mark.parametrize('rid,amount,qty,urgency,before,after',[
 ('5.4','500','10','Normal','SPOT_PO','RFQ'),
 ('5.3','500','3000','Emergency','EMERGENCY_PO','RFQ'),
 ('5.5','2000000','10000','Normal','RFP','RFQ')])
def test_threshold_mutation(data,policy,rid,amount,qty,urgency,before,after):
    rows=[line(quantity=qty,urgency=urgency)]
    assert process(rows,data,[policy])['rows'][0]['route']==before
    def walk(n):
        if n.get('fact')=='requirement.group_value_inr': n['value']=amount
        for c in n.get('all',[]): walk(c)
    for r in policy['rules']:
        if r['id']==rid: walk(r['when'])
    assert process(rows,data,[policy])['rows'][0]['route']==after

def test_precedence_mutation(data,policy):
    data.contracts=[contract()]
    assert process([line()],data,[policy])['rows'][0]['route']=='CONTRACT_PO'
    policy['rules'].append({'id':'special','priority':-1,'when':condition('item.category','eq','Bearings'),'route':'RFQ','reason':'New mandatory safety review'})
    result=process([line()],data,[policy])
    assert result['rows'][0]['route']=='RFQ' and not result['allocations']

def test_chat_multiturn_and_correction(data):
    state,reply=parse_message({},'Need bearings',data)
    assert not state.get('ready')
    state,reply=parse_message(state,'6205-2RS around 400',data)
    assert state['item_code']=='I-A' and state['quantity']=='400'
    state,reply=parse_message(state,'P-A 2026-12-01 not urgent',data)
    assert state['ready'] and state['urgency']=='Normal'
    state,reply=parse_message(state,'quantity 500',data)
    assert state['quantity']=='500'
    state,reply=parse_message(state,'cancel',data)
    assert state=={}

def test_new_item_price_followup(data):
    state,reply=parse_message({},'new item specialised purifier need 1 at P-A by 2026-12-01 normal',data)
    assert state['item_code']=='NEW' and not state.get('ready')
    state,reply=parse_message(state,'price 9000',data)
    assert state['estimated_unit_price']=='9000' and state['ready']

def test_malformed_policy_is_validation_error(policy):
    with pytest.raises(ValueError): validate_policy({'rules':[]})

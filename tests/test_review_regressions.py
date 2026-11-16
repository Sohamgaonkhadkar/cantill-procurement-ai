from copy import deepcopy
import pytest
from backend.amendments import propose
from backend.chat import parse_message

@pytest.mark.parametrize('text',[
    'At plant P-A require RFQ for Bearings items above INR 75000',
    'If the category is Bearings, set spot limit to INR 75000',
    'Do not change the spot limit to INR 75000',
    'Emergency limit is unchanged at INR 75000',
    'For Bearings require RFQ above INR 75000',
    'RFQ limit is INR 75000 for capital equipment',
    'Change spot limit from INR 200000 to INR 75000',
])
def test_scoped_or_negated_amendment_never_changes_global_rules(policy,text):
    before=deepcopy(policy['rules'])
    result,changes=propose(policy,text,'6.0','2026-11-01')
    assert result['rules']==before
    assert changes==[]

def test_chat_replaces_selected_item_after_correction(data):
    state={'description':'Ball bearing 6205-2RS','item_code':'I-A','quantity':'10','plant':'P-A','need_by_date':'2026-12-01','urgency':'Normal','ready':True,'uom':'NOS'}
    state,reply=parse_message(state,'Actually change the item to hydraulic hose 1/2 inch 2 wire',data)
    assert state['item_code']=='I-B'
    assert state['uom']=='MTR'
    assert 'Hydraulic hose' in reply and 'Ball bearing' not in reply

def test_unresolved_item_correction_clears_confirmation(data):
    state={'description':'Ball bearing 6205-2RS','item_code':'I-A','quantity':'10','plant':'P-A','need_by_date':'2026-12-01','urgency':'Normal','ready':True,'uom':'NOS'}
    state,reply=parse_message(state,'Change the item to an unspecified different component',data)
    assert not state.get('item_code') and not state.get('ready')

def test_non_item_followup_keeps_selected_item(data):
    state={'description':'Ball bearing 6205-2RS','item_code':'I-A','quantity':'10','plant':'P-A','need_by_date':'2026-12-01','urgency':'Normal','ready':True,'uom':'NOS'}
    state,reply=parse_message(state,'Actually quantity 25',data)
    assert state['item_code']=='I-A' and state['quantity']=='25'

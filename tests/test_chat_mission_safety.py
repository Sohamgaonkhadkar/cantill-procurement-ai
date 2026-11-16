import pytest
from backend.chat import parse_message

@pytest.mark.parametrize('message',['quantity -5','need -5 units','qty 0','quantity 1e999999','quantity NaN','qty abc'])
def test_invalid_quantity_corrections_clear_stale_values(data,message):
    state={'item_code':'I-A','quantity':'10','plant':'P-A','need_by_date':'2026-12-20','urgency':'Normal','ready':True}
    changed,reply=parse_message(state,message,data)
    assert not changed.get('ready') and not changed.get('quantity')
    assert 'quantity' in reply.lower()
    assert state['quantity']=='10'

def test_quantity_is_not_misused_as_an_item_dimension(data):
    state,reply=parse_message({},'need 0.5 hydraulic hose 2 wire P-A tomorrow Normal',data)
    assert state.get('item_code')!='I-B' and not state.get('ready')
    state,reply=parse_message({},'need 10 hydraulic hose 1/2 inch 2 wire P-A tomorrow Normal',data)
    assert state.get('item_code')=='I-B' and state['quantity']=='10'

def test_multiple_and_negated_plant_names_do_not_choose_silently(data):
    changed,reply=parse_message({},'need 10 bearing 6205-2RS P-A and P-B tomorrow Normal',data)
    assert not changed.get('plant') and not changed.get('ready') and 'multiple plants' in reply
    changed,reply=parse_message({'plant':'P-A','ready':True},'not P-A, use P-B',data)
    assert changed['plant']=='P-B'

def test_explicit_model_replacement_and_ambiguity(data):
    changed,reply=parse_message({'item_code':'I-A','ready':True},'change item from I-A to I-B',data)
    assert changed['item_code']=='I-B'
    changed,reply=parse_message({},'I-A or I-B',data)
    assert not changed.get('item_code') and 'multiple item codes' in reply
    changed,reply=parse_message({'item_code':'I-A','ready':True},'not I-A',data)
    assert not changed.get('item_code') and not changed.get('ready')

def test_negative_new_item_estimate_cannot_reuse_old_price(data):
    changed,reply=parse_message({'item_code':'NEW','estimated_unit_price':'100','ready':True},'price -50',data)
    assert not changed.get('estimated_unit_price') and not changed.get('ready')

from backend.chat import parse_message

def test_model_number_not_interpreted_as_quantity(data):
    state,reply=parse_message({},'Need 6205-2RS bearings at P-A by 2026-12-01 normal',data)
    assert not state.get('quantity') and not state.get('ready')

def test_new_item_unit_is_requested_not_invented(data):
    state,reply=parse_message({},'new item specialised purifier need 1 at P-A by 2026-12-01 normal price 9000',data)
    assert state['item_code']=='NEW' and not state.get('ready')
    assert 'unit of measure' in reply
    state,reply=parse_message(state,'NOS',data)
    assert state['ready'] and state['uom']=='NOS'

def test_negated_emergency_and_quantity_correction(data):
    state,reply=parse_message({},'Need 10 bearing 6205-2RS at P-A by 2026-12-01 not emergency',data)
    assert state['urgency']=='Normal'
    state,reply=parse_message(state,'make it 25',data)
    assert state['quantity']=='25'

def test_wrong_model_suffix_does_not_select_catalog_item(data):
    state,reply=parse_message({},'Need 10 bearing 6205-2RZ at P-A by 2026-12-01 normal',data)
    assert not state.get('item_code') and not state.get('ready')

def test_bad_date_correction_clears_confirmation_readiness(data):
    state,reply=parse_message({},'Need 10 bearing 6205-2RS at P-A by 2026-12-01 normal',data)
    assert state['ready']
    for correction in ['need by 2026-02-30','need it in 99999999999999999999 days']:
        corrected,reply=parse_message(state,correction,data)
        assert not corrected.get('ready') and not corrected.get('need_by_date')

def test_unknown_code_correction_clears_old_selection(data):
    state,reply=parse_message({},'Need 10 bearing 6205-2RS at P-A by 2026-12-01 normal',data)
    assert state['ready']
    corrected,reply=parse_message(state,'change item to ITM-999999',data)
    assert not corrected.get('ready') and not corrected.get('item_code')

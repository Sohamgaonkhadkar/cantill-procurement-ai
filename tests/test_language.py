from copy import deepcopy
import pytest
from backend.language import interpret
from backend.engine import process
from conftest import line

def test_scoped_clause_compiles_and_changes_only_matching_plant(data,policy):
    original=deepcopy(policy)
    result=interpret(policy,'If the plant is P-A, the category is Bearings, and the requirement value exceeds INR 750, require RFQ','6.0','2026-04-01',data)
    assert result['complete'] and len(result['detected_changes'])==1
    changed=result['policy']
    a=process([line()],data,[changed])
    b=process([line(plant='P-B')],data,[changed])
    assert a['rows'][0]['route']=='RFQ' and b['rows'][0]['route']=='SPOT_PO'
    assert policy==original

@pytest.mark.parametrize('word,qty,expected',[
    ('exceeds','10','SPOT_PO'),('at least','10','RFQ'),('below','10','SPOT_PO'),('at most','10','RFQ')])
def test_scoped_operators_have_exact_boundaries(data,policy,word,qty,expected):
    p=interpret(policy,f'If plant is P-A and value {word} INR 1000 require RFQ','6.0','2026-04-01',data)['policy']
    assert process([line(quantity=qty)],data,[p])['rows'][0]['route']==expected

def test_parameters_and_indian_amounts(data,policy):
    result=interpret(policy,'Change spot limit to INR 1,50,000\nSet grouping window to 5 days\nSuggest 2 suppliers for RFQ','6.0','2026-04-01',data)
    assert result['complete'] and len(result['detected_changes'])==3
    assert result['policy']['parameters']['group_days']==5
    assert result['policy']['parameters']['suggestions']['RFQ']==2
    assert result['policy']['rules'][4]['when']['all'][0]['value']=='150000'

def test_unknown_scope_and_qualifiers_remain_unresolved(data,policy):
    for text in ['If plant is UNKNOWN and value above INR 750 require RFQ','Change spot limit from INR 199999 to INR 75000','For Bearings require RFQ above INR 75000','If plant is P-A unless emergency require RFQ']:
        result=interpret(policy,text,'6.0','2026-04-01',data)
        if 'unless emergency' in text:
            assert result['complete'] and not result['unresolved_clauses']
            assert process([line()],data,[result['policy']])['rows'][0]['route']=='RFQ'
            assert process([line(urgency='Emergency')],data,[result['policy']])['rows'][0]['route']=='EMERGENCY_PO'
            assert process([line(plant='P-B')],data,[result['policy']])['rows'][0]['route']=='SPOT_PO'
            continue
        assert not result['complete'] and result['unresolved_clauses']
        assert result['policy']['rules']==policy['rules']

def test_boolean_or_and_not(data,policy):
    p=interpret(policy,'If plant is P-A or not urgency is normal require RFQ','6.0','2026-04-01',data)
    assert p['complete']
    assert process([line(plant='P-B',urgency='Emergency')],data,[p['policy']])['rows'][0]['route']=='RFQ'

def test_partial_document_accounts_for_every_clause(data,policy):
    p=interpret(policy,'Change spot limit to INR 75000\nA legal exception needing buyer judgment applies','6.0','2026-04-01',data)
    assert len(p['detected_changes'])==1 and len(p['unresolved_clauses'])==1 and not p['complete']

def test_wrapped_pdf_clause_is_compiled_as_one_statement(data,policy):
    p=interpret(policy,'If the plant is P-A,\nthe category is Bearings, and\nthe requirement value exceeds INR 750, require RFQ','6.0','2026-04-01',data)
    assert p['complete'] and len(p['detected_changes'])==1

def test_diff_identifies_changed_amount_field(policy):
    from backend.amendments import field_diff
    after=deepcopy(policy); after['rules'][4]['when']['all'][0]['value']='75000'
    diff=field_diff(policy,after)
    assert diff==[{'path':'rules[5.4].when.all[0].value','before':'200000','after':'75000'}]

def test_policy_diff_does_not_recursively_copy_governance(policy):
    from backend.amendments import policy_diff
    before={**policy,'governance':{'source_text':'prior document','diff':[{'before':{'governance':{'source_text':'older document'}}}]}}
    after={**policy,'version':'6.0'}
    assert policy_diff(before,after)==[{'path':'version','before':'5.0','after':'6.0'}]

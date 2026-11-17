from copy import deepcopy
import pytest
from backend.language import interpret

@pytest.mark.parametrize('text,value',[
 ('Change the spot purchasing limit from INR 200000 to INR 175000','175000'),
 ('Reduce spot limit from 2 lakh to 1.75 lakh','175000'),
 ('Increase spot limit from ₹2,00,000 to ₹2,50,000','250000'),
 ('The spot purchasing limit shall now be ₹1,75,000','175000'),
 ('The revised limit for spot purchases is 1.75 lakh','175000'),
 ('Replace the existing spot threshold with INR 175000','175000'),
 ('Change RFP threshold from 10,00,000 to 12,00,000','1200000'),
])
def test_equivalent_global_wording_preserves_eligibility_and_operators(policy,data,text,value):
    before=deepcopy(policy)
    result=interpret(policy,text,'6','2026-11-01',data)
    assert result['complete'],result
    rules=result['policy']['rules']
    if 'RFP' in text:
        assert rules[5]['when']['value']==rules[6]['when']['value']==value
        assert rules[5]['when']['op']=='lt' and rules[6]['when']['op']=='gte'
    else:
        assert rules[4]['when']['all'][0]=={'fact':'requirement.group_value_inr','op':'lt','value':value}
        assert rules[4]['when']['all'][1]==before['rules'][4]['when']['all'][1]
        assert rules[:4]+rules[5:]==before['rules'][:4]+before['rules'][5:]
    assert policy==before

@pytest.mark.parametrize('text',[
 'Change spot limit from INR 199999 to INR 175000',
 'Increase spot limit from INR 200000 to INR 175000',
 'Reduce spot limit from INR 200000 to INR 250000',
])
def test_prior_value_and_direction_conflicts_never_apply(policy,data,text):
    result=interpret(policy,text,'6','2026-11-01',data)
    assert not result['complete'] and result['conflicts']
    assert result['policy']['rules']==policy['rules']

def test_exact_comparators_and_post_clause_scope(policy,data):
    r=interpret(policy,'Only purchases exceeding ₹1,75,000 require RFQ\nPurchases up to and including 2 lakh qualify for SPOT_PO','6','2026-11-01',data)
    assert r['complete']
    assert r['policy']['rules'][5]['when']['all'][1]['op']=='gt'
    assert r['policy']['rules'][4]['when']['all'][0]['op']=='lte'
    r=interpret(policy,'If category Bearings and value at least 75000 require RFQ\nApply this rule only to the Alpha plant\nThe previous rule remains unchanged for other categories','6','2026-11-01',data)
    assert r['complete'],r
    assert r['policy']['rules'][:-1]==policy['rules']
    assert r['policy']['rules'][-1]['when']['all'][1]=={'fact':'requirement.plant','op':'eq','value':'P-A'}

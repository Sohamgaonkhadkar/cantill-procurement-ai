"""Prior-value and direction checks for explicit supplier-count amendments."""
from copy import deepcopy
import pytest
from backend.language import interpret


@pytest.mark.parametrize('text',[
    'Change supplier count for RFQ from four to five',
    'Increase preferred supplier count for RFQ from three to two',
    'Increase supplier count for RFQ to two',
])
def test_conflicting_supplier_count_wording_does_not_mutate_policy(policy,data,text):
    before=deepcopy(policy)
    result=interpret(policy,text,'FINAL-6','2026-11-01',data)
    assert not result['complete'] and result['conflicts']
    assert result['policy']['parameters']==before['parameters']
    assert policy==before


@pytest.mark.parametrize('text',[
    'Increase preferred supplier count for RFQ from three to five',
    'Change supplier count for RFQ from 3 to 5',
    'Set supplier count for RFQ to five',
])
def test_consistent_supplier_count_wording_preserves_other_routes(policy,data,text):
    result=interpret(policy,text,'FINAL-6','2026-11-01',data)
    assert result['complete'],result
    assert result['policy']['parameters']['suggestions']==dict(policy['parameters']['suggestions'],RFQ=5)
    assert result['policy']['rules']==policy['rules']

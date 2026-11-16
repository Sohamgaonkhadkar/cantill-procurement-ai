import pytest
from backend.domain import number
from backend.matching import resolve
from backend.engine import process
from conftest import line

@pytest.mark.parametrize('value',['1e999999','1e-999999','1,2,3','abc','Infinity','9'*200])
def test_invalid_numeric_inputs_are_explicit_errors(value):
    with pytest.raises(ValueError): number(value)

def test_indian_and_western_numeric_grouping():
    assert number('20,00,000')==number('2,000,000')==number('2000000')

def test_partial_item_requires_clarification(data):
    code,evidence=resolve('','bearing 6205','NOS',data.items)
    assert code=='NEW' and evidence.get('error') and evidence['candidates'][0]['item_code']=='I-A'

def test_equivalent_inch_fraction_and_model_suffix_protection(data):
    assert resolve('','hyd hose 0.5 inches 2 wire','MTR',data.items)[0]=='I-B'
    assert resolve('','Ball bearing 6205-2RZ','NOS',data.items)[0]=='NEW'

def test_hyphenated_and_spaced_bearing_shields_are_equivalent(data):
    data.items['I-D']={**data.items['I-A'],'description':'Roller bearing 8120-ZZ'}
    assert resolve('','roller brg 8120 ZZ','NOS',data.items)[0]=='I-D'

def test_huge_quantity_retained_without_decimal_overflow(data,policy):
    result=process([line(quantity='1e999999')],data,[policy])
    assert result['rows'][0]['route']=='NOT_PROCESSED' and len(result['rows'])==1

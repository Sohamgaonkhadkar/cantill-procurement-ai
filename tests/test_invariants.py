from copy import deepcopy
from backend.domain import digest
from backend.engine import process
from conftest import line,contract

def test_snapshot_hash_independent_of_database_row_order(data):
    data.history += [{**data.history[0],'po_number':'H-B','po_date':'2026-09-01'}]
    data.contracts=[contract('C-B'),contract('C-A')]
    first=digest(data.snapshot())
    data.history.reverse(); data.contracts.reverse()
    assert digest(data.snapshot())==first

def test_equal_rate_contract_tie_and_full_precision(data,policy):
    data.contracts=[contract('C-Z',lines=[{'item_code':'I-A','rate':'90.1234','uom':'NOS'}]),contract('C-A',supplier_id='S-B',lines=[{'item_code':'I-A','rate':'90.1234','uom':'NOS'}])]
    result=process([line(quantity='3')],data,[policy])
    assert result['rows'][0]['supplier_id']=='S-B'
    assert result['rows'][0]['unit_price']=='90.1234'
    assert result['requirements'][0]['evidence']['valuation']['exact_value']=='270.3702'
    assert result['rows'][0]['group_value_inr']=='270.37'

def test_auto_and_explicit_same_policy_output(data,policy):
    rows=[line(quantity='0'),line('PR-B')]
    assert process(rows,data,[policy])['rows']==process(rows,data,[policy],'5.0')['rows']

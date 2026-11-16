"""Synthetic independent expectations and metamorphic checks; no assessment fixtures."""
from copy import deepcopy
from decimal import Decimal
from random import Random
from datetime import datetime,date
import pytest
from backend.domain import Data,number
from backend.engine import process
from backend.matching import resolve
from conftest import line,contract

@pytest.mark.parametrize('amount,urgency,expected',[
    ('199999.99','Normal','SPOT_PO'),('200000.00','Normal','RFQ'),('200000.01','Normal','RFQ'),
    ('999999.99','Normal','RFQ'),('1000000.00','Normal','RFP'),('1000000.01','Normal','RFP'),
    ('499999.99','Emergency','EMERGENCY_PO'),('500000.00','Emergency','EMERGENCY_PO'),('500000.01','Emergency','RFQ'),
    ('199999.99','Emergency','EMERGENCY_PO'),('200000.00','Emergency','EMERGENCY_PO'),('1000000.00','Emergency','RFP'),
])
def test_independently_derived_threshold_table(data,policy,amount,urgency,expected):
    data.items['I-A']['standard_price']='1';data.history[0]['unit_price']='1'
    result=process([line(quantity=amount,urgency=urgency)],data,[policy])
    assert result['rows'][0]['route']==expected
    assert result['rows'][0]['group_value_inr']==amount
    assert result['requirements'][0]['evidence']['valuation']['exact_value']==amount


def test_independent_competing_ceiling_allocation(data,policy):
    data.contracts=[contract('LOW',value_cap='100',lines=[{'item_code':'I-A','rate':'10','uom':'NOS'}]),contract('HIGH',supplier_id='S-B',value_cap='200',lines=[{'item_code':'I-A','rate':'20','uom':'NOS'}])]
    rows=[line('SYN-A',quantity='6'),line('SYN-B',quantity='3',need_by_date='2026-12-20'),line('SYN-C',quantity='2',need_by_date='2027-01-20'),line('SYN-D',quantity='10',need_by_date='2027-02-20')]
    result=process(rows,data,[policy]);out=result['rows']
    assert [(row['route'],row['supplier_id'],row['unit_price']) for row in out]==[('CONTRACT_PO','S-A','10.00'),('CONTRACT_PO','S-A','10.00'),('CONTRACT_PO','S-B','20.00'),('SPOT_PO','S-A','100.00')]
    assert result['allocations']=={'LOW':'90','HIGH':'40'}
    assert out[-1]['group_value_inr']=='100.00'  # lowest exhausted applicable benchmark, not PO reference price


def test_500_synthetic_lines_multiplant_contracts_and_shuffling(data,policy):
    rng=Random(8192)
    data.contracts=[contract('C-LOW',value_cap='35000',lines=[{'item_code':'I-A','uom':'NOS','rate':'90'}]),contract('C-HIGH',supplier_id='S-B',value_cap='80000',lines=[{'item_code':'I-A','uom':'NOS','rate':'95'}])]
    rows=[]
    for index in range(500):
        code=rng.choice(['I-A','I-B','I-C']);item=data.items[code]
        rows.append(line(f'SYNTHETIC-500-{index:04}',item_code=code,description=item['description'],uom=item['uom'],quantity=str(rng.randint(1,300)),plant=rng.choice(['P-A','P-B']),created_at=f'2026-11-{rng.randint(1,28):02} {rng.randint(0,23):02}:00',need_by_date=f'2026-12-{rng.randint(1,28):02}',urgency=rng.choice(['Normal','Emergency'])))
    first=process(rows,data,[policy]);shuffled=deepcopy(rows);rng.shuffle(shuffled);second=process(shuffled,data,[policy])
    assert first==second
    assert len(first['rows'])==500 and len({(r['pr_no'],r['pr_line']) for r in first['rows']})==500
    assert all(row['supplier_id']!='S-X' and 'S-X' not in row['suggested_supplier_ids'] for row in first['rows'])
    caps={c['contract_id']:number(c['value_cap'])-number(c['consumed_value']) for c in data.contracts}
    assert all(number(amount)<=caps[cid] for cid,amount in first['allocations'].items())
    seen=set()
    for req in first['requirements']:
        anchor=req['evidence']['group_anchor']
        for raw in req['lines']:
            key=(raw['pr_no'],raw['pr_line']);assert key not in seen;seen.add(key)
            assert raw['plant']==anchor['plant'] and raw['item_code']==anchor['item_code']
            assert 0<=(datetime.fromisoformat(raw['created_at'])-datetime.fromisoformat(anchor['created_at'])).days<=14
            assert abs((date.fromisoformat(raw['need_by_date'])-date.fromisoformat(anchor['need_by_date'])).days)<=7
        assert Decimal(req['quantity'])==sum(Decimal(raw['quantity']) for raw in req['lines'])
    assert len(seen)==500


def test_local_plant_amendment_leaves_other_plant_business_fields_unchanged(data,policy):
    rows=[line('SYN-A',plant='P-A'),line('SYN-B',plant='P-B')]
    before=process(rows,data,[policy]);changed=deepcopy(policy);changed['version']='6.0'
    changed['rules'].append({'id':'plant-only','priority':1,'when':{'fact':'requirement.plant','op':'eq','value':'P-A'},'route':'RFP','reason':'Synthetic plant-only amendment'})
    after=process(rows,data,[changed]);b=next(r for r in before['rows'] if r['pr_no']=='SYN-B');a=next(r for r in after['rows'] if r['pr_no']=='SYN-B')
    for field in ['group_id','po_id','route','supplier_id','unit_price','group_value_inr','suggested_supplier_ids']:assert a[field]==b[field]


def test_industrial_aliases_mixed_fractions_and_spec_protection(data):
    data.items['SYN-SS']={'item_code':'SYN-SS','description':'Stainless steel bolt M10x30','uom':'NOS','category':'Fasteners','item_type':'Material','standard_price':'10'}
    data.items['SYN-HOSE']={'item_code':'SYN-HOSE','description':'Hydraulic hose 1.5 inch 2 wire','uom':'MTR','category':'Hydraulics','item_type':'Material','standard_price':'20'}
    assert resolve('','SS bolt M10 x 30','NOS',data.items)[0]=='SYN-SS'
    assert resolve('','hyd hose 1 1/2 inch 2 wire','MTR',data.items)[0]=='SYN-HOSE'
    assert resolve('','hyd hose 1.50in 2 wire','MTR',data.items)[0]=='SYN-HOSE'
    assert resolve('','SS bolt M10x35','NOS',data.items)[0]=='NEW'
    assert resolve('','hyd hose 1.6 inch 2 wire','MTR',data.items)[0]=='NEW'
    assert resolve('','SS bolt M10x30','MTR',data.items)[0]=='NEW'

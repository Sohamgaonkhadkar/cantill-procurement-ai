from copy import deepcopy
from datetime import date,timedelta
from decimal import Decimal as D
import random
import pytest
from backend.engine import process
from backend.matching import resolve,normalize
from backend.policy import evaluate,validate_policy,condition,matches
from backend.suppliers import history_for,preferred
from backend.domain import csv_bytes,read_csv,OUTPUT_COLUMNS
from conftest import line,contract

def run(rows,data,policy): return process(rows,data,[policy])

def test_normalization(data):
    assert resolve('','brg 6205 2rs for maintenance','NOS',data.items)[0]=='I-A'
    assert resolve('','hyd hose 1/2 inch 2 wire','MTR',data.items)[0]=='I-B'
    assert resolve('','brg 6308 zz','NOS',data.items)[0]=='NEW'
    assert resolve('I-A','wrong description','NOS',data.items)[0]=='I-A'
    assert resolve('INVALID','bearing 6205 2rs','NOS',data.items)[1]['error']

@pytest.mark.parametrize('days,need,same',[(14,7,True),(15,7,False),(14,8,False),(0,-7,True),(0,-8,False)])
def test_group_boundaries(data,policy,days,need,same):
    a=line(); b=line('PR-B',created_at=(date(2026,11,1)+timedelta(days=days)).isoformat()+' 10:01',need_by_date=(date(2026,11,20)+timedelta(days=need)).isoformat())
    result=run([b,a],data,policy)
    assert (result['rows'][0]['group_id']==result['rows'][1]['group_id'])==same

def test_anchor_nontransitive(data,policy):
    result=run([line(),line('PR-B',created_at='2026-11-10 10:00'),line('PR-C',created_at='2026-11-20 10:00')],data,policy)
    assert len(result['requirements'])==2

def test_different_plant_emergency(data,policy):
    result=run([line(),line('PR-B',plant='P-B'),line('PR-C',urgency='Emergency')],data,policy)
    assert len(result['requirements'])==2
    assert result['requirements'][0]['route']=='EMERGENCY_PO'

def test_multiple_eligible_earliest(data,policy):
    rows=[line(need_by_date='2026-11-10'),line('PR-B',need_by_date='2026-11-22',created_at='2026-11-02 10:00'),line('PR-C',need_by_date='2026-11-16',created_at='2026-11-03 10:00')]
    result=run(rows,data,policy)
    assert [len(g['lines']) for g in result['requirements']]==[2,1]

def test_new_items_never_grouped(data,policy):
    rows=[line(pr,item_code='',description='Uncatalogued widget',estimated_unit_price='12.34') for pr in ['PR-A','PR-B']]
    result=run(rows,data,policy)
    assert len(result['requirements'])==2
    assert all(r['route']=='NEW_ITEM_SOURCING' and r['suggested_supplier_ids']=='' for r in result['rows'])

@pytest.mark.parametrize('changes',[{'quantity':'0'},{'quantity':'-1'},{'quantity':'NaN'},{'plant':'unknown'},{'item_code':'invalid'},{'uom':'KG'},{'created_at':'bad'},{'urgency':'Urgent'},{'item_code':'','description':'new thing','estimated_unit_price':''}])
def test_invalid_lines_retained(data,policy,changes):
    r=run([line(**changes)],data,policy)
    assert len(r['rows'])==1 and r['rows'][0]['route']=='NOT_PROCESSED'

def test_duplicate_line_numbers(data,policy):
    assert len(run([line(),line(pr_line='2')],data,policy)['issues'])==0
    r=run([line(),line()],data,policy)
    assert len(r['rows'])==2 and len(r['issues'])==2

def test_exact_ceiling_and_simulation(data,policy):
    data.contracts=[contract(value_cap='900')]
    before=deepcopy(data.snapshot()); r=run([line()],data,policy)
    assert r['rows'][0]['route']=='CONTRACT_PO'
    assert r['allocations']=={'C-A':'900'}
    assert data.snapshot()==before
    assert run([line()],data,policy)==r

def test_contract_chronology_competition(data,policy):
    data.contracts=[contract(value_cap='900'),contract('C-B',supplier_id='S-B',lines=[{'item_code':'I-A','uom':'NOS','rate':'95'}])]
    result=run([line('PR-B',created_at='2026-11-20 10:00'),line()],data,policy)
    assert [r['supplier_id'] for r in result['rows']]==['S-A','S-B']
    assert result['allocations']=={'C-A':'900','C-B':'950'}

def test_exhausted_contract_valuation(data,policy):
    data.contracts=[contract(value_cap='1')]
    result=run([line(quantity='3000')],data,policy)
    assert result['rows'][0]['route']=='RFQ'
    assert result['rows'][0]['group_value_inr']=='270000.00'
    assert result['allocations']=={}

@pytest.mark.parametrize('start,end,sid,eligible',[('2026-11-01','2026-11-01','S-A',True),('2026-11-02','2027-01-01','S-A',False),('2026-01-01','2026-10-31','S-A',False),('2026-01-01','2027-01-01','S-X',False)])
def test_contract_validity(data,policy,start,end,sid,eligible):
    data.contracts=[contract(start_date=start,end_date=end,supplier_id=sid)]
    assert (run([line()],data,policy)['rows'][0]['route']=='CONTRACT_PO')==eligible

def test_capex_no_ceiling_allocation(data,policy):
    data.contracts=[contract(lines=[{'item_code':'I-C','uom':'NOS','rate':'100'}])]
    result=run([line(item_code='I-C')],data,policy)
    assert result['rows'][0]['route']=='CAPEX_SOURCING' and result['allocations']=={}

@pytest.mark.parametrize('qty,urgency,route',[('1999.99','Normal','SPOT_PO'),('2000','Normal','RFQ'),('5000','Emergency','EMERGENCY_PO'),('5000.01','Emergency','RFQ'),('10000','Normal','RFP')])
def test_thresholds(data,policy,qty,urgency,route): assert run([line(quantity=qty,urgency=urgency)],data,policy)['rows'][0]['route']==route

def test_history_boundaries(data,policy):
    data.history[0]['po_date']='2025-11-01'
    assert history_for(data,'I-A',date(2026,11,1),365)
    data.history[0]['po_date']='2025-10-31'
    assert not history_for(data,'I-A',date(2026,11,1),365)
    data.history[0]['po_date']='2026-11-01'
    assert not history_for(data,'I-A',date(2026,11,1),365)
    data.history[0]['po_date']='2026-11-02'
    assert not history_for(data,'I-A',date(2026,11,1),365)

def test_blocked_price_history_not_eligibility(data,policy):
    data.history[0]['supplier_id']='S-X'
    r=run([line()],data,policy)
    assert r['rows'][0]['route']=='RFQ'
    assert r['requirements'][0]['evidence']['valuation']['source']=='historical_po'
    assert 'S-X' not in r['rows'][0]['suggested_supplier_ids']

def test_po_consolidation_separate_from_grouping(data,policy):
    rows=[line(),line('PR-B',created_at='2026-11-02 10:00',need_by_date='2026-12-20')]
    r=run(rows,data,policy)
    assert len(r['requirements'])==2 and len(r['orders'])==1
    rows[1]['created_at']='2026-11-02 10:01'
    assert len(run(rows,data,policy)['orders'])==2

def test_determinism_and_supplier_invariants(data,policy):
    data.contracts=[contract()]
    rows=[line('PR-'+str(i),created_at=f'2026-11-{i+1:02} 10:00',need_by_date=f'2026-12-{i+1:02}') for i in range(20)]
    before=run(rows,data,policy)
    random.Random(42).shuffle(rows)
    assert run(rows,data,policy)==before
    assert len(before['rows'])==20
    assert all(number<=D('100000') for number in map(D,before['allocations'].values()))
    assert all(r['supplier_id']!='S-X' and 'S-X' not in r['suggested_supplier_ids'] for r in before['rows'])

def test_rule_language_validation(policy):
    for node in [{'fact':'os.system','op':'eq','value':'x'},{'fact':'item.category','op':'exec','value':'x'}]:
        broken=deepcopy(policy); broken['rules'][0]['when']=node
        with pytest.raises(ValueError): validate_policy(broken)
    assert matches({'all':[{'not':condition('item.category','eq','Safety')},{'any':[condition('requirement.group_value_inr','gt','10'),condition('requirement.plant','in',['P-A'])]}]},{'item.category':'Bearings','requirement.group_value_inr':'20','requirement.plant':'P-B'})
    assert matches(condition('contract.selected_supplier_id','is_null',None),{})

def test_plant_category_mutation(data,policy):
    before=run([line()],data,policy)
    changed=deepcopy(policy); changed['version']='6.0'
    changed['rules'].insert(0,{'id':'new','priority':-1,'route':'RFQ','reason':'Plant-specific review','when':{'all':[condition('requirement.plant','eq','P-A'),condition('item.category','eq','Bearings'),condition('requirement.group_value_inr','gt','750')]}})
    validate_policy(changed)
    assert before['rows'][0]['route']=='SPOT_PO'
    assert run([line()],data,changed)['rows'][0]['route']=='RFQ'

def test_policy_effective_and_unapproved(data,policy):
    changed=deepcopy(policy); changed.update(version='6.0',effective_date='2026-12-01',status='active')
    changed['rules'][4]['when']['all'][0]['value']='0'
    assert process([line()],data,[policy,changed])['rows'][0]['policy_version']=='5.0'
    changed.update(effective_date='2026-01-01',status='draft')
    assert process([line()],data,[policy,changed])['rows'][0]['policy_version']=='5.0'

def test_parameter_mutations(data,policy):
    rows=[line(),line('PR-B',created_at='2026-11-10 10:00')]
    assert len(run(rows,data,policy)['requirements'])==1
    policy['parameters']['group_days']=2
    assert len(run(rows,data,policy)['requirements'])==2
    policy['parameters']['suggestions']['RFQ']=1
    r=run([line(quantity='3000')],data,policy)
    assert len(r['rows'][0]['suggested_supplier_ids'].split(';'))==1
    policy['parameters']['history_days']=1
    assert run([line()],data,policy)['rows'][0]['route']=='RFQ'

def test_csv_format(data,policy):
    rows=run([line()],data,policy)['rows']; exported=csv_bytes(rows)
    assert exported.decode().splitlines()[0]==','.join(OUTPUT_COLUMNS)
    assert read_csv(exported)==rows

def test_reference_contract_no_future(data,policy):
    data.history=[]; data.contracts=[contract(end_date='2026-03-01'),contract('C-FUTURE',start_date='2026-12-01')]
    ranking=preferred(data,'I-A',date(2026,11,1),policy)
    assert ranking[0]['reference_source']=='C-A'

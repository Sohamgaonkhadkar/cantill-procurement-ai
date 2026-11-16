from random import Random
from decimal import Decimal
import pytest
from backend.engine import process
from conftest import line,contract

@pytest.mark.parametrize('seed',range(8))
def test_generated_batches_preserve_financial_and_identity_invariants(data,policy,seed):
    random=Random(seed); data.contracts=[contract(value_cap='15000')]
    rows=[line(f'SYN-{i:04}',quantity=str(random.randint(1,40)),plant=random.choice(['P-A','P-B']),created_at=f'2026-11-{random.randint(1,27):02} 10:00',need_by_date=f'2026-12-{random.randint(1,27):02}',urgency=random.choice(['Normal','Emergency'])) for i in range(70)]
    first=process(rows,data,[policy]); random.shuffle(rows); second=process(rows,data,[policy])
    assert first['rows']==second['rows'] and first['output_hash']==second['output_hash']
    assert len(first['rows'])==len(rows) and len({r['pr_no'] for r in first['rows']})==len(rows)
    assert all(Decimal(x)<=15000 for x in first['allocations'].values())
    for group in first['requirements']:
        assert Decimal(group['quantity'])==sum(Decimal(r['quantity']) for r in group['lines'])
        valuation=group['evidence']['valuation']
        assert Decimal(valuation['exact_value'])==Decimal(group['quantity'])*Decimal(valuation['unit_price'])
        assert group['supplier_id']!='S-X' and 'S-X' not in group['suggested_supplier_ids']

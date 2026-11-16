from copy import deepcopy
import csv
import io
import pytest
from backend.domain import csv_bytes, INPUT_COLUMNS, OUTPUT_COLUMNS
from backend.engine import process
from conftest import line
from scripts.validate_submission import validate, PREFERRED_COLUMNS


@pytest.fixture
def exports(tmp_path, data, policy):
    rows=[line('SYNTHETIC-A'),line('SYNTHETIC-B')]
    changed=deepcopy(policy);changed['version']='6.0';changed['rules'][4]['when']['all'][0]['value']='500'
    paths={key:tmp_path/(key+'.csv') for key in ['input','run1','run2','preferred','suppliers']}
    paths['input'].write_bytes(csv_bytes(rows,INPUT_COLUMNS))
    paths['run1'].write_bytes(csv_bytes(process(rows,data,[policy])['rows']))
    paths['run2'].write_bytes(csv_bytes(process(rows,data,[changed])['rows']))
    paths['preferred'].write_bytes(csv_bytes([{'item_code':'I-A','rank':'1','supplier_id':'S-A','reference_price':'100.00'}],PREFERRED_COLUMNS))
    paths['suppliers'].write_bytes(csv_bytes(list(data.suppliers.values()),['supplier_id','status']))
    return paths


def check(paths):
    return validate(paths['input'],paths['run1'],paths['run2'],paths['preferred'],'6.0',paths['suppliers'])


def mutate(paths,name,change,columns=OUTPUT_COLUMNS):
    rows=list(csv.DictReader(io.StringIO(paths[name].read_text())))
    change(rows)
    paths[name].write_bytes(csv_bytes(rows,columns))


def test_real_engine_exports_pass_structural_validation(exports):
    result=check(exports)
    assert result['valid'] and result['run1']['rows']==2 and result['run2']['rows']==2
    assert result['supplier_status_checked']


@pytest.mark.parametrize('kind',['missing_line','duplicate_line','wrong_policy','nonfinite','blocked_supplier','inconsistent_group','bad_header'])
def test_export_corruption_is_rejected(exports,kind):
    if kind=='missing_line':change=lambda rows:rows.pop()
    elif kind=='duplicate_line':change=lambda rows:rows.append(rows[0])
    elif kind=='wrong_policy':change=lambda rows:rows[0].update(policy_version='wrong')
    elif kind=='nonfinite':change=lambda rows:rows[0].update(group_value_inr='NaN')
    elif kind=='blocked_supplier':change=lambda rows:rows[0].update(supplier_id='S-X')
    elif kind=='inconsistent_group':change=lambda rows:rows[0].update(group_value_inr='999.99')
    else:
        exports['run1'].write_text('wrong,headers\na,b\n')
        with pytest.raises(ValueError):check(exports)
        return
    mutate(exports,'run1',change)
    with pytest.raises(ValueError):check(exports)


def test_preferred_duplicate_and_rank_gap_are_rejected(exports):
    mutate(exports,'preferred',lambda rows:rows.append(rows[0]),PREFERRED_COLUMNS)
    with pytest.raises(ValueError,match='duplicate suppliers or non-contiguous'):check(exports)


def test_duplicate_input_identities_are_retained_when_not_processed(exports):
    rows=list(csv.DictReader(io.StringIO(exports['input'].read_text())))
    rows[1]=rows[0].copy();exports['input'].write_bytes(csv_bytes(rows,INPUT_COLUMNS))
    for name in ['run1','run2']:
        invalid=[{key:'' for key in OUTPUT_COLUMNS} for _ in rows]
        for row in invalid:row.update(pr_no=rows[0]['pr_no'],pr_line='1',route='NOT_PROCESSED',reason='Duplicate PR line identity')
        exports[name].write_bytes(csv_bytes(invalid))
    assert check(exports)['run1']['rows']==2

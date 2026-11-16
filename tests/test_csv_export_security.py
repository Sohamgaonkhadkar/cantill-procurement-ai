import csv,io
import pytest
from backend.domain import csv_bytes,read_csv

@pytest.mark.parametrize('value',['=HYPERLINK("https://invalid.example")','+SUM(1,2)','-cmd|x','@SUM(1,2)',' \t=1+1'])
def test_all_text_columns_are_spreadsheet_safe(value):
    payload=csv_bytes([{'pr_no':value,'supplier_id':value,'policy_version':value,'reason':value,'unit_price':'12.50','group_value_inr':'100.00'}],['pr_no','supplier_id','policy_version','reason','unit_price','group_value_inr'])
    row=next(csv.DictReader(io.StringIO(payload.decode())))
    for key in ['pr_no','supplier_id','policy_version','reason']:assert row[key]=="'"+value
    assert row['unit_price']=='12.50' and row['group_value_inr']=='100.00'

@pytest.mark.parametrize('payload',[b'a,b\n"unclosed,2',b'a,b\nx\x00y,z',b'a\n'+b'x'*140000])
def test_malformed_csv_is_controlled_validation(payload):
    with pytest.raises(ValueError):read_csv(payload)

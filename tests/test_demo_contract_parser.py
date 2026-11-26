"""Post-assessment regression coverage for fictional contract extraction."""
import pytest
from backend import ingest
from backend.demo import dataset
from backend.workspace import assert_demo_text,WrongWorkspaceError

GUIDE="""CORVO / FICTIONAL DEMONSTRATION ONLY Sample supply agreement
No real supplier, legal obligation or verified signature is represented.
Contract ID DEMO-GUIDE-CONTRACT-9B696C4
Supplier ID DEMO-S-B Supplier name Demo Engineering Partners
Valid from 2026-11-01 Valid through 2027-12-31
Value cap (INR) 10000 Consumed value (INR) 0
Item code DEMO-BEARING Description Demo ball bearing 6205-2RS
Unit of measure NOS Unit rate (INR) 85
Scope: fictional DEMO-PLANT testing only."""

STANDARD="""FICTIONAL DEMONSTRATION ONLY
Contract No. DEMO-TEST-CONTRACT-2026-11
Supplier ID DEMO-S-B
valid from 2026-11-01 to 2027-12-31
not exceed INR 20,000
1 DEMO-HOSE Demo hydraulic hose 1/2 inch MTR 150
"""

@pytest.mark.parametrize('source,item,uom,rate,cap',[
    (GUIDE,'DEMO-BEARING','NOS','85','10000'),
    (' '.join(GUIDE.split()),'DEMO-BEARING','NOS','85','10000'),
    (STANDARD,'DEMO-HOSE','MTR','150','20000'),
])
def test_demo_contract_extraction(monkeypatch,source,item,uom,rate,cap):
    assert_demo_text(source)
    monkeypatch.setattr(ingest,'pdf_text',lambda content:source)
    parsed=ingest.extract_contract(b'%PDF-test',demo=True)
    assert ingest.validate_contract(parsed,dataset())==parsed
    assert parsed['supplier_id']=='DEMO-S-B'
    assert parsed['value_cap']==cap and parsed['consumed_value']=='0'
    assert parsed['lines'][0]['item_code']==item
    assert parsed['lines'][0]['uom']==uom and parsed['lines'][0]['rate']==rate
    assert parsed['provenance']['signature_verified'] is False
    with pytest.raises(ValueError):ingest.extract_contract(b'%PDF-test')

def test_missing_demo_field_requires_manual_review(monkeypatch):
    monkeypatch.setattr(ingest,'pdf_text',lambda content:GUIDE.replace('Supplier ID DEMO-S-B','Supplier unavailable'))
    with pytest.raises(ValueError,match='supplier_id'):ingest.extract_contract(b'%PDF-test',demo=True)

def test_demo_security_and_master_validation_still_apply(monkeypatch):
    with pytest.raises(WrongWorkspaceError):assert_demo_text('Contract No. RC-2026-001')
    monkeypatch.setattr(ingest,'pdf_text',lambda content:GUIDE.replace('DEMO-S-B','DEMO-S-UNKNOWN'))
    with pytest.raises(ValueError,match='Unknown contract supplier'):
        ingest.validate_contract(ingest.extract_contract(b'%PDF-test',demo=True),dataset())

def test_assessment_parser_unchanged(monkeypatch):
    source='Contract No. RC-2026-999999\nSupplier ID S999999\nvalid from 2026-11-01 to 2027-12-31\nnot exceed INR 20,000\n1 ITM-999999 Fictional test hose MTR 150\n'
    monkeypatch.setattr(ingest,'pdf_text',lambda content:source)
    parsed=ingest.extract_contract(b'%PDF-test')
    assert parsed['contract_id']=='RC-2026-999999'
    assert parsed['supplier_id']=='S999999'
    assert parsed['lines'][0]['item_code']=='ITM-999999'
    with pytest.raises(ValueError):ingest.extract_contract(b'%PDF-test',demo=True)

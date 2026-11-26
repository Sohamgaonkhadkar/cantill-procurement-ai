"""Post-assessment regression coverage for fictional contract extraction."""
import io
import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
from backend import ingest
from backend.demo import dataset
from backend.workspace import assert_demo_text,WrongWorkspaceError
from test_api import client

def pdf(source):
    """Generate a real text PDF and exercise pypdf's extraction path."""
    writer=PdfWriter(); page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    commands=['BT /F1 10 Tf 40 750 Td 16 TL']
    for line in source.splitlines():
        escaped=line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        commands.append('('+escaped+') Tj T*')
    commands.append('ET'); stream=DecodedStreamObject();stream.set_data('\n'.join(commands).encode('ascii'))
    page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output);return output.getvalue()

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
def test_demo_contract_extraction(source,item,uom,rate,cap):
    assert_demo_text(source)
    raw=pdf(source)
    parsed=ingest.extract_contract(raw,demo=True)
    assert ingest.validate_contract(parsed,dataset())==parsed
    assert parsed['supplier_id']=='DEMO-S-B'
    assert parsed['start_date']=='2026-11-01' and parsed['end_date']=='2027-12-31'
    assert parsed['lines'][0]['description'].startswith('Demo ')
    assert parsed['value_cap']==cap and parsed['consumed_value']=='0'
    assert parsed['lines'][0]['item_code']==item
    assert parsed['lines'][0]['uom']==uom and parsed['lines'][0]['rate']==rate
    assert parsed['provenance']['signature_verified'] is False
    with pytest.raises(ValueError):ingest.extract_contract(raw)

def test_missing_demo_field_requires_manual_review():
    raw=pdf(GUIDE.replace('Supplier ID DEMO-S-B','Supplier unavailable'))
    with pytest.raises(ValueError,match='supplier_id'):ingest.extract_contract(raw,demo=True)

def test_demo_security_and_master_validation_still_apply():
    with pytest.raises(WrongWorkspaceError):assert_demo_text('Contract No. RC-2026-001')
    with pytest.raises(ValueError,match='Unknown contract supplier'):
        ingest.validate_contract(ingest.extract_contract(pdf(GUIDE.replace('DEMO-S-B','DEMO-S-UNKNOWN')),demo=True),dataset())

def test_assessment_parser_unchanged():
    source='Contract No. RC-2026-999999\nSupplier ID S999999\nvalid from 2026-11-01 to 2027-12-31\nnot exceed INR 20,000\n1 ITM-999999 Fictional test hose MTR 150\n'
    raw=pdf(source); parsed=ingest.extract_contract(raw)
    assert parsed['contract_id']=='RC-2026-999999'
    assert parsed['supplier_id']=='S999999'
    assert parsed['lines'][0]['item_code']=='ITM-999999'
    with pytest.raises(ValueError):ingest.extract_contract(raw,demo=True)

def test_consumption_is_extracted_without_silent_zero():
    raw=pdf(GUIDE.replace('Consumed value (INR) 0','Consumed value (INR) 1,234.56'))
    assert ingest.extract_contract(raw,demo=True)['consumed_value']=='1234.56'
    for invalid in ('-5','1.2.3','unknown'):
        with pytest.raises(ValueError,match='consumed_value'):
            ingest.extract_contract(pdf(GUIDE.replace('Consumed value (INR) 0','Consumed value (INR) '+invalid)),demo=True)

@pytest.mark.parametrize('before,after',[
    ('Value cap (INR) 10000','Value cap (INR) 10000.2.3'),
    ('Unit rate (INR) 85','Unit rate (INR) 85.2.3'),
])
def test_malformed_money_cannot_be_partially_extracted(before,after):
    with pytest.raises(ValueError):ingest.extract_contract(pdf(GUIDE.replace(before,after)),demo=True)

def test_invalid_second_line_cannot_silently_disappear():
    source=GUIDE+'\nItem code DEMO-HOSE Description Demo hose\nUnit of measure MTR Unit rate (INR) unknown\n'
    with pytest.raises(ValueError,match='Incomplete demo contract lines'):
        ingest.extract_contract(pdf(source),demo=True)

def test_multiple_valid_contract_lines_are_preserved():
    source=GUIDE+'\nItem code DEMO-HOSE Description Demo hose\nUnit of measure MTR Unit rate (INR) 150\n'
    parsed=ingest.validate_contract(ingest.extract_contract(pdf(source),demo=True),dataset())
    assert [x['item_code'] for x in parsed['lines']]==['DEMO-BEARING','DEMO-HOSE']

def test_demo_upload_populates_pending_proposal_and_preserves_guards(client,monkeypatch):
    from backend import api
    from backend.service import save_data
    # Only test routing selects demo parsing; no production isolation configuration changes.
    monkeypatch.setattr(api,'isolated_demo',lambda:True)
    with api.Session.begin() as s: save_data(s,dataset())
    before=client.get('/api/contracts').json()['total']
    response=client.post('/api/contracts/upload',files={'file':('demo.pdf',pdf(GUIDE),'application/pdf')})
    assert response.status_code==200,response.text
    proposal=response.json()
    assert proposal['status']=='pending_review' and not proposal['manual_entry_required']
    assert proposal['validation_error'] is None and not proposal['signature_verified']
    assert proposal['contract']['contract_id']=='DEMO-GUIDE-CONTRACT-9B696C4'
    assert proposal['contract']['lines'][0]['rate']=='85'
    assert client.get('/api/contracts').json()['total']==before
    assert any(e['action']=='contract.uploaded' and e['details']['proposal_id']==proposal['id'] for e in client.get('/api/audit').json()['items'])
    assert any(p['id']==proposal['id'] and p['status']=='pending_review' for p in client.get('/api/contracts/proposals').json()['items'])
    malformed=client.post('/api/contracts/upload',files={'file':('manual.pdf',pdf('Fictional demonstration: manual transcription required'),'application/pdf')}).json()
    assert malformed['manual_entry_required'] and malformed['contract'] is None
    unknown=client.post('/api/contracts/upload',files={'file':('unknown.pdf',pdf(GUIDE.replace('DEMO-S-B','DEMO-S-UNKNOWN')),'application/pdf')}).json()
    assert unknown['manual_entry_required'] and unknown['validation_error']=='Unknown contract supplier'
    rejected=client.post('/api/contracts/upload',files={'file':('private.pdf',pdf(GUIDE+'\nRC-2026-001'),'application/pdf')})
    assert rejected.status_code==422
    monkeypatch.setattr(api,'isolated_demo',lambda:False)
    token=client.post('/api/auth/login',json={'role':'requester','password':'corvo-demo'}).json()['access_token']
    assert client.post('/api/contracts/upload',headers={'Authorization':'Bearer '+token},files={'file':('demo.pdf',pdf(GUIDE),'application/pdf')}).status_code==403

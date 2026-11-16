import io,json
import os
from copy import deepcopy
from fastapi.testclient import TestClient
import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
from backend import api
from backend.db import connect,Base,ContractLedger,PurchaseOrder
from backend.service import save_data
from backend.domain import csv_bytes,INPUT_COLUMNS
from conftest import line,contract

@pytest.fixture
def client(tmp_path,monkeypatch,data):
    test_url=os.getenv('TEST_DATABASE_URL')
    if test_url and not test_url.endswith('/corvo_test'): raise RuntimeError('PostgreSQL test database must be explicitly named corvo_test')
    engine,session=connect(test_url or 'sqlite:///'+str(tmp_path/'test.db'))
    if test_url: Base.metadata.drop_all(engine)
    monkeypatch.setattr(api,'engine',engine); monkeypatch.setattr(api,'Session',session)
    with TestClient(api.app) as client:
        with session.begin() as s: save_data(s,data)
        token=client.post('/api/auth/login',json={'role':'admin','password':'corvo-demo'}).json()['access_token']
        client.headers['Authorization']='Bearer '+token
        yield client
    engine.dispose()

def upload(client,rows=None,version='5.0'):
    return client.post('/api/process-batch',files={'file':('synthetic.csv',csv_bytes(rows or [line()],INPUT_COLUMNS),'text/csv')},data={'policy_version':version})

def test_batch_persistence_exports_replay(client):
    response=upload(client); assert response.status_code==200,response.text
    result=response.json(); rid=result['id']
    assert upload(client).json()['id']==rid
    assert client.get('/api/runs').json()['total']==1
    assert client.get('/api/runs/'+rid).json()['output_hash']==result['output_hash']
    assert client.get('/api/runs/'+rid+'/replay').status_code==405
    assert client.post('/api/runs/'+rid+'/replay').json()['matches']
    assert client.get('/api/runs/'+rid+'/export.csv').text.startswith('pr_no,pr_line,')
    req=result['requirements'][0]
    detail=client.get(f"/api/requirements/{req['id']}",params={'run_id':rid}).json()
    assert detail['evidence']['valuation']['exact_value']=='1000'
    assert client.get('/api/overview').json()['runs']==1

def test_policy_upload_review_approve_activate_compare(client):
    before=upload(client).json(); p=client.get('/api/policies').json()['items'][0]
    p={k:v for k,v in p.items() if k not in {'status','id'}}; p['version']='6.0'
    p['rules'][4]['when']['all'][0]['value']='500'
    response=client.post('/api/policies/upload-amendment',files={'file':('amendment.json',json.dumps(p),'application/json')},data={'version':'6.0','effective_date':'2026-04-01'})
    assert response.status_code==200,response.text
    assert upload(client,version='6.0').json()['rows'][0]['route']=='NOT_PROCESSED'
    sim=client.post('/api/policies/6.0/simulate',json={'run_id':before['id']})
    assert sim.status_code==200,sim.text
    assert sim.json()['comparison']['affected_lines']==1
    assert client.post('/api/policies/6.0/approve',json={'reason':'Verified source clauses'}).status_code==409
    assert client.post('/api/policies/6.0/review',json={'reason':'Verified source clauses'}).status_code==200
    assert client.post('/api/policies/6.0/approve',json={'reason':'Approved threshold change'}).status_code==200
    assert upload(client,version='6.0').json()['rows'][0]['route']=='NOT_PROCESSED'
    assert client.post('/api/policies/6.0/activate',json={'reason':'Activate reviewed version'}).status_code==200
    after=upload(client,version='6.0').json()
    assert after['rows'][0]['route']=='RFQ'
    assert client.get(f"/api/runs/{before['id']}/compare/{after['id']}").json()['affected_lines']==1
    assert client.post(f"/api/runs/{before['id']}/replay").json()['matches']
    assert client.put('/api/policies/6.0',json={'policy':p}).status_code==409
    assert client.post('/api/policies/6.0/deactivate',json={'reason':'Withdraw test amendment after comparison'}).status_code==200
    assert upload(client,version='6.0').json()['rows'][0]['route']=='RFQ'

def test_approval_actual_po_idempotence_and_audit(client):
    result=upload(client).json(); req=result['requirements'][0]['id']; url=f'/api/requirements/{req}/approve?run_id='+result['id']
    response=client.post(url,json={'reason':'Buyer verified requirement'})
    assert response.status_code==200,response.text
    assert client.get('/api/purchase-orders').json()['total']==1
    assert client.post(url,json={'reason':'Buyer verified requirement'}).status_code==409
    assert client.get('/api/audit').json()['total']>=2
    assert client.post(f"/api/runs/{result['id']}/replay").json()['matches']

def test_override_preserves_recommendation(client):
    result=upload(client).json(); req=result['requirements'][0]['id']
    url=f'/api/requirements/{req}/override?run_id='+result['id']
    assert client.post(url,json={'route':'RFQ','reason':''}).status_code==422
    response=client.post(url,json={'route':'RFQ','reason':'Obtain fresh competitive offers'})
    assert response.status_code==200,response.text
    assert client.get('/api/sourcing').json()['total']==1
    assert client.get('/api/runs/'+result['id']).json()['rows'][0]['route']=='SPOT_PO'

def test_contract_ledger_approval_recheck(client,data):
    with api.Session.begin() as s:
        data.contracts=[contract(value_cap='900')]; save_data(s,data)
    result=upload(client).json(); assert result['allocations']=={'C-A':'900'}
    with api.Session() as s: assert len(s.query(ContractLedger).all())==0
    req=result['requirements'][0]['id']; response=client.post(f'/api/requirements/{req}/approve',params={'run_id':result['id']},json={'reason':'Buyer verified signed rate'})
    assert response.status_code==200,response.text
    assert client.get('/api/contracts').json()['items'][0]['remaining_value']=='0'
    assert upload(client,[line('PR-NEXT',created_at='2026-11-02 11:00')]).json()['rows'][0]['route']=='SPOT_PO'
    assert client.post(f"/api/runs/{result['id']}/replay").json()['matches']

def pdf_bytes():
    writer=PdfWriter(); page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    lines=['RATE CONTRACT','Contract No. RC-2099-001','Supplier ID S-A','valid from 2026-01-01 to 2027-12-31','not exceed INR 1,00,000','1 I-A Ball bearing 6205-2RS NOS 90.00']
    # Real-kit parser intentionally expects canonical IDs; tests of extraction use
    # canonical synthetic master records, never supplied records.
    lines=[x.replace('S-A','S901').replace('I-A','ITM-9001') for x in lines]
    stream=DecodedStreamObject(); stream.set_data(('BT /F1 10 Tf 50 740 Td '+' '.join('('+x+') Tj 0 -15 Td' for x in lines)+' ET').encode())
    page[NameObject('/Contents')]=writer._add_object(stream)
    out=io.BytesIO(); writer.write(out); return out.getvalue()

def test_contract_pdf_ingestion(client,data):
    data.suppliers['S901']={**data.suppliers['S-A'],'supplier_id':'S901'}
    data.items['ITM-9001']={**data.items['I-A'],'item_code':'ITM-9001'}
    with api.Session.begin() as s: save_data(s,data)
    response=client.post('/api/contracts/upload',files={'file':('synthetic.pdf',pdf_bytes(),'application/pdf')})
    assert response.status_code==200,response.text
    proposal=response.json(); assert proposal['contract']['value_cap']=='100000'
    response=client.post('/api/contracts/proposals/'+proposal['id']+'/approve',json={'contract':proposal['contract'],'reason':'Verified signed original manually'})
    assert response.status_code==200,response.text
    assert client.get('/api/contracts').json()['total']==1

def test_chat_confirmation_creates_real_pr(client):
    response=client.post('/api/chat/messages',json={'message':'Need 10 ball bearing 6205-2RS at P-A by 2026-12-01 normal'})
    assert response.status_code==200,response.text
    chat=response.json(); assert chat['state']['ready'],chat
    assert chat['run'] is None
    response=client.post('/api/chat/messages',json={'session_id':chat['session_id'],'message':'confirm'})
    assert response.status_code==200,response.text
    assert response.json()['run']['rows'][0]['route']=='SPOT_PO'

def test_auth_cors_validation(client):
    token=client.post('/api/auth/login',json={'role':'requester','password':'corvo-demo'}).json()['access_token']
    from backend.policy import initial_policy
    response=client.post('/api/policies',headers={'Authorization':'Bearer '+token},json={'policy':initial_policy()})
    assert response.status_code==403
    assert client.get('/api/runs',headers={'Authorization':'Bearer wrong'}).status_code==401
    assert client.get('/api/requirements?limit=500').status_code==422
    response=client.options('/api/runs',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'Authorization'})
    assert response.status_code==200
    assert response.headers['access-control-allow-origin']=='http://localhost:5173'
    assert client.post('/api/process-batch',files={'file':('bad.csv','bad,columns\n1,2','text/csv')}).status_code==422

def test_preferred_export_and_openapi(client):
    response=client.get('/api/preferred-suppliers',params={'as_of':'2026-11-01','item_code':'I-A'})
    assert response.status_code==200 and response.json()['items'][0]['supplier_id']=='S-A'
    assert client.get('/api/preferred-suppliers/export.csv?as_of=2026-11-01').text.startswith('item_code,rank,supplier_id,reference_price\n')
    schema=client.get('/openapi.json').json()
    assert 'Evidence' in schema['components']['schemas']
    assert schema['paths']['/api/process-batch']['post']['security']==[{'HTTPBearer':[]}]

def test_text_amendment_and_bad_documents(client):
    response=client.post('/api/policies/propose-amendment',json={'text':'Change spot limit to INR 75000','version':'5.1','effective_date':'2026-11-01'})
    assert response.status_code==200,response.text
    assert response.json()['interpretation']['detected_changes']
    assert response.json()['rules'][4]['when']['all'][0]['value']=='75000'
    response=client.post('/api/contracts/upload',files={'file':('bad.pdf',b'%PDF-broken','application/pdf')})
    assert response.status_code==422
    assert response.json()['error']['code']=='VALIDATION_ERROR'

def test_private_import_paths_and_idempotence(client,data):
    import zipfile
    def archive(path,payload):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z: z.writestr(path,payload)
        return stream.getvalue()
    response=client.post('/api/admin/import-data',files={'file':('unsafe.zip',archive('../escape.csv','x'),'application/zip')})
    assert response.status_code==422
    response=client.post('/api/admin/import-data',files={'file':('broken.zip',b'not a zip','application/zip')})
    assert response.status_code==422
    stream=io.BytesIO()
    from backend.domain import csv_bytes
    for supplier in data.suppliers.values(): supplier['city']='Synthetic City'
    with zipfile.ZipFile(stream,'w') as z:
        for filename,rows in [('master_data/item_master.csv',list(data.items.values())),('master_data/supplier_master.csv',list(data.suppliers.values())),('master_data/plants.csv',list(data.plants.values())),('master_data/po_history.csv',data.history)]:
            z.writestr('synthetic/'+filename,csv_bytes(rows,list(rows[0])))
        z.writestr('synthetic/contracts/contract_register.csv','contract_id,supplier_id,start_date,end_date,value_cap,consumed_value\n')
        z.writestr('synthetic/contracts/contract_lines.csv','contract_id,item_code,description,uom,rate\n')
    for _ in range(2):
        response=client.post('/api/admin/import-data',files={'file':('synthetic.zip',stream.getvalue(),'application/zip')})
        assert response.status_code==200,response.text
        assert response.json()['items']==3 and response.json()['history_rows']==1

def test_openapi_snapshot_is_current():
    from pathlib import Path
    assert json.loads(Path('openapi.json').read_text(encoding='utf-8'))==api.app.openapi()

import hashlib
from test_api import client
from backend import api
from backend.service import save_data
from conftest import contract

def test_direct_contract_detail_matches_register_and_missing_is_404(client,data):
    data.contracts=[contract()]
    with api.Session.begin() as s:save_data(s,data)
    detail=client.get('/api/contracts/C-A',params={'as_of':'2026-11-01'})
    assert detail.status_code==200
    register=client.get('/api/contracts',params={'as_of':'2026-11-01'}).json()['items'][0]
    assert detail.json()==register
    assert client.get('/api/contracts/unknown').status_code==404
    assert client.get('/api/contracts/proposals').status_code==200

def test_amendment_retains_exact_uploaded_source_hash(client):
    raw=b'Set spot limit to INR 75000\r\n'
    response=client.post('/api/policies/upload-amendment',files={'file':('amendment.txt',raw,'text/plain')},data={'version':'source-evidence','effective_date':'2026-04-01'})
    assert response.status_code==200
    gov=response.json()['governance']
    assert gov['source_bytes_hash']==hashlib.sha256(raw).hexdigest()
    saved=next(p for p in client.get('/api/policies').json()['items'] if p['version']=='source-evidence')
    assert saved['governance']['source_bytes_hash']==gov['source_bytes_hash']

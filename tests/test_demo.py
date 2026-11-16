import csv,io
from sqlalchemy import select,func
from backend import api
from backend.demo import dataset,batch
from backend.domain import csv_bytes,INPUT_COLUMNS,OUTPUT_COLUMNS
from backend.engine import process
from backend.policy import initial_policy
from backend.schemas import ProcessingResult
from backend.db import Run,RequirementRecord,PurchaseOrder,ContractLedger,Policy,Item
from test_api import client


def state():
    with api.Session() as s:
        return [s.scalar(select(func.count()).select_from(model)) for model in [Run,RequirementRecord,PurchaseOrder,ContractLedger,Policy,Item]]


def test_demo_computed_by_engine_and_isolated_from_live_records(client):
    before=state()
    response=client.post('/api/demo/preview')
    assert response.status_code==200,response.text
    body=response.json()
    assert body['mode']=='synthetic_preview' and body['persistent'] is False
    assert body['result']==ProcessingResult.model_validate(process(batch(),dataset(),[initial_policy()],'5.0')).model_dump()
    assert len(body['result']['rows'])==9
    assert set(body['result']['counts'])=={'CONTRACT_PO','SPOT_PO','EMERGENCY_PO','RFQ','RFP','CAPEX_SOURCING','NEW_ITEM_SOURCING','NOT_PROCESSED'}
    assert 'DEMO-S-BLOCKED' not in str(body['result']['rows'])
    assert state()==before


def test_demo_quantity_changes_output_and_export_agrees(client):
    rows=[batch()[2]]
    def preview(rows):
        r=client.post('/api/demo/preview',files={'file':('demo.csv',csv_bytes(rows,INPUT_COLUMNS),'text/csv')})
        assert r.status_code==200,r.text
        return r.json()['result']
    before=preview(rows);rows[0]['quantity']='50000';after=preview(rows)
    assert before['rows'][0]['route']=='SPOT_PO' and after['rows'][0]['route']=='RFP'
    assert before['output_hash']!=after['output_hash']
    export=client.post('/api/demo/export.csv',files={'file':('demo.csv',csv_bytes(rows,INPUT_COLUMNS),'text/csv')})
    assert export.status_code==200
    assert list(csv.DictReader(io.StringIO(export.text)))==after['rows']
    assert export.text.splitlines()[0]==','.join(OUTPUT_COLUMNS)


def test_demo_input_download_and_auth_validation(client):
    download=client.get('/api/demo/input.csv')
    assert download.status_code==200 and len(list(csv.DictReader(io.StringIO(download.text))))==9
    client.headers.clear()
    assert client.get('/api/demo/input.csv').status_code==401
    assert client.post('/api/demo/preview').status_code==401
    assert client.post('/api/demo/export.csv').status_code==401


def test_demo_does_not_accept_live_master_item_as_demo_data(client):
    row={**batch()[0],'item_code':'I-A','plant':'P-A'}
    before=state()
    result=client.post('/api/demo/preview',files={'file':('live.csv',csv_bytes([row],INPUT_COLUMNS),'text/csv')})
    assert result.status_code==200 and result.json()['result']['rows'][0]['route']=='NOT_PROCESSED'
    assert state()==before
    invalid=client.post('/api/demo/preview',files={'file':('bad.csv',b'quantity,quantity\n1,2','text/csv')})
    assert invalid.status_code==422


def test_demo_bounds_do_not_change_ordinary_batch_limits(client):
    rows=[{**batch()[2],'pr_no':'DEMO-LIMIT-'+str(index)} for index in range(201)]
    response=client.post('/api/demo/preview',files={'file':('large-demo.csv',csv_bytes(rows,INPUT_COLUMNS),'text/csv')})
    assert response.status_code==422 and 'at most 200' in response.text

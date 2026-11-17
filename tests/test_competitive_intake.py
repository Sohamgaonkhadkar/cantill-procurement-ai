from copy import deepcopy
import pytest
from backend.chat import parse_message
from backend.matching import resolve
from backend import api
from backend.domain import csv_bytes,INPUT_COLUMNS
from backend.db import Run,Chat,Policy
from sqlalchemy import select,func
from test_api import client
from conftest import line

@pytest.mark.parametrize('text,value',[('I need twenty bearings','20'),('Get fifty pairs of gloves','50'),('Make that thirty-five instead','35'),('I need 2 dozen bolts','24'),('Need five hundred metres of hose','500'),('quantity two lakh','200000')])
def test_local_spoken_quantities_preserve_confirmed_fields(data,text,value):
    original={'item_code':'I-A','quantity':'10','plant':'P-A','need_by_date':'2026-12-01','urgency':'Emergency'}
    state,_=parse_message(original,text,data)
    assert state['quantity']==value
    for field in ['plant','need_by_date','urgency']:assert state[field]==original[field]
    assert original['quantity']=='10'

def test_local_ambiguous_weekday_and_model_corrections(data):
    original={'item_code':'I-A','quantity':'10','plant':'P-A','need_by_date':'2026-12-01','urgency':'Emergency','ready':True}
    state,reply=parse_message(original,'I need this by next Friday',data)
    assert not state.get('need_by_date') and not state.get('ready') and 'or' in reply and 'YYYY-MM-DD' in reply
    for text in ['Actually, not the 6205 bearing','Use the other bearing model']:
        state,reply=parse_message(original,text,data)
        assert not state.get('item_code') and not state['ready']
        for field in ['quantity','plant','need_by_date','urgency']:assert state[field]==original[field]
    assert parse_message(original,'That is normal, not emergency',data)[0]['urgency']=='Normal'

def test_matching_categories_and_dimension_integrity(data):
    data.items['BOLT']={'description':'Stainless steel bolt M10x40 grade 8.8','uom':'NOS'}
    assert resolve('i-a','','NOS',data.items)[0]=='I-A'
    assert resolve('invalid','','NOS',data.items)[1]['classification']=='invalid_code'
    assert resolve('','SS bolt M10x40 grade 8.8','NOS',data.items)[0]=='BOLT'
    for text in ['Ball bearing','Stainless steel bolt M10']:
        assert resolve('',text,'NOS',data.items)[1]['classification']=='partial_catalog'
    for text in ['Ball bearing 6205-2RZ','Custom laser scanner']:
        assert resolve('',text,'NOS',data.items)[1]['classification']=='new_item'
    assert resolve('','Ball bearing 6205-2RS','MTR',data.items)[1]['classification']=='unit_conflict'

def test_wrong_demo_workspace_rejects_before_business_storage(client,monkeypatch):
    def counts():
        with api.Session() as s:return [s.scalar(select(func.count()).select_from(model)) for model in [Run,Chat,Policy]]
    before=counts();monkeypatch.setattr(api,'isolated_demo',lambda:True)
    response=client.post('/api/process-batch',files={'file':('challenge.csv',csv_bytes([line(item_code='ITM-1001',plant='CHK1')],INPUT_COLUMNS),'text/csv')})
    assert response.status_code==422 and response.json()['error']['code']=='WRONG_WORKSPACE'
    assert client.post('/api/chat/messages',json={'message':'Need ITM-1001 at CHK1'}).status_code==422
    assert client.post('/api/policies/propose-amendment',json={'text':'Set a new threshold for CHK1','version':'blocked','effective_date':'2026-11-17'}).status_code==422
    assert counts()==before

def test_policy_conversation_handoff_has_no_write_or_activation(client,monkeypatch):
    monkeypatch.setenv('RAG_ENABLED','true')
    before=client.get('/api/policies').json()
    source='Change the spot purchasing limit from INR 200000 to INR 175000'
    response=client.post('/api/chat/messages',json={'message':source})
    assert response.status_code==200,response.text
    assert response.json()['state']['policy_proposal_text']==source and response.json()['run'] is None
    assert client.get('/api/policies').json()==before
    from backend.proposals import handoff
    assert 'policy_proposal_text' not in handoff({},source,'requester')[0]

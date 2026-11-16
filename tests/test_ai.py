"""Synthetic privacy, grounding, concurrency and real-engine integration checks."""
from copy import deepcopy
from decimal import Decimal
from threading import Event,Thread
from types import SimpleNamespace
import json,time
import pytest
from backend import api
from backend.db import Chat,ChatTurn,KnowledgeDocument,KnowledgeChunk,AIUsage
from backend.ai import safety
from backend.ai.provider import Provider,ProviderResult
from backend.ai.schemas import IntentPlan,GroundedAnswer
from backend.ai.intent import validate_updates,spoken_number
from backend.ai.retrieval import search
from backend.ai.knowledge import sync_core_sources,store_document
from backend.ai.grounding import validate_answer
from backend.ai.tools import execute
from backend.ai.budget import reserve,settle,BudgetExceeded
from backend.security import Principal
from test_api import client

@pytest.fixture(autouse=True)
def local_ai(monkeypatch):
    monkeypatch.setenv('AI_CHAT_ENABLED','true');monkeypatch.setenv('RAG_ENABLED','true')
    monkeypatch.setenv('AI_EXTERNAL_CALLS_ENABLED','false')

def chat(client,message,**fields):
    return client.post('/api/chat/messages',json={'message':message,**fields})

def test_live_external_denied_before_client(monkeypatch):
    monkeypatch.setenv('AI_EXTERNAL_CALLS_ENABLED','true');monkeypatch.setattr(safety,'isolated_demo',lambda:False)
    monkeypatch.setattr(Provider,'_client',lambda _:pytest.fail('Private content reached SDK'))
    with pytest.raises(safety.PrivacyBoundaryError):Provider(None,None).structured([{'role':'user','content':'Private supplier'}],IntentPlan,safety.ExternalContext(True,('fictional_demo',),True))

@pytest.mark.parametrize('context,text',[
    (safety.ExternalContext(False,('fictional_demo',),True),'hello'),
    (safety.ExternalContext(True,('private',),True),'hello'),
    (safety.ExternalContext(True,('fictional_demo',),False),'hello'),
    (safety.ExternalContext(True,('fictional_demo',),True),'Look up ITM-1001'),
    (safety.ExternalContext(True,('fictional_demo',),True),'password: this-is-a-private-value'),
])
def test_demo_privacy_gates(context,text,monkeypatch):
    monkeypatch.setattr(safety,'isolated_demo',lambda:True);monkeypatch.setenv('AI_EXTERNAL_CALLS_ENABLED','true')
    with pytest.raises(safety.PrivacyBoundaryError):safety.assert_external_allowed(context,text)

def test_live_knowledge_yes_never_creates_pr(client,monkeypatch):
    monkeypatch.setattr(Provider,'_client',lambda _:pytest.fail('Live chat used external API'))
    result=chat(client,'What is the current policy?').json()
    assert result['mode']=='knowledge' and result['grounded'] and result['citations']
    answer=chat(client,'yes',session_id=result['session_id']).json()
    assert answer['run'] is None and answer['ai_status']=='local_only'
    assert chat(client,'yes',session_id=result['session_id']).json()['run'] is None

def test_model_cannot_redirect_policy_question_to_unrelated_tools(client,monkeypatch):
    monkeypatch.setenv('AI_EXTERNAL_CALLS_ENABLED','true');monkeypatch.setattr(safety,'isolated_demo',lambda:True)
    monkeypatch.setattr(Provider,'structured',lambda *args:ProviderResult(IntentPlan(intent='general_procurement_question'),'mock',1,1,1))
    monkeypatch.setattr(Provider,'tool_calls',lambda *args:[{'name':'get_recent_user_requests','arguments':'{}'}])
    # Live fixture provenance is intentionally not external-safe, so synthesis
    # remains local even though its intent/tool planner is mocked as available.
    result=chat(client,'What is the current policy?',demo_data_acknowledged=True).json()
    assert result['tools_used']==['get_active_policy'] and '5.0' in result['message']

def test_real_confirmation_retry_is_idempotent(client):
    result=chat(client,'Need 10 units I-A P-A 2099-11-20 Normal').json()
    assert result['state']['ready'],result
    body={'session_id':result['session_id'],'expected_revision':result['revision'],'request_id':'confirm-retry-0001','action':'confirm'}
    confirmed=chat(client,'confirm',**body)
    assert confirmed.status_code==200,confirmed.text
    assert confirmed.json()['run']['rows'] and confirmed.json()['state']=={}
    assert chat(client,'confirm',**body).json()==confirmed.json()
    assert chat(client,'changed',**body).status_code==409
    assert chat(client,'hello',session_id=result['session_id'],expected_revision=0).status_code==409

def test_lease_blocks_concurrent_turns_without_database_transaction(client,monkeypatch):
    monkeypatch.setenv('AI_EXTERNAL_CALLS_ENABLED','true');monkeypatch.setattr(safety,'isolated_demo',lambda:True)
    entered=Event();release=Event();responses=[]
    def planned(self,messages,schema,context):
        assert api.engine.pool.checkedout()==0
        entered.set();assert release.wait(8)
        return ProviderResult(IntentPlan(intent='create_purchase_request'), 'mock',0,0,1)
    monkeypatch.setattr(Provider,'structured',planned)
    first=chat(client,'hello').json()
    worker=Thread(target=lambda:responses.append(chat(client,'Need bearings',session_id=first['session_id'],demo_data_acknowledged=True)))
    worker.start();assert entered.wait(8)
    try:assert chat(client,'other turn',session_id=first['session_id']).status_code==409
    finally:release.set();worker.join(10)
    assert responses[0].status_code==200

def test_owner_source_acl_review_hash_and_search(client):
    meta={'title':'Synthetic safety reference','source_type':'guideline','visibility':'owner'}
    raw=b'Synthetic safety: inspect a bearing guard before installation.'
    upload=lambda:client.post('/api/knowledge/documents',files={'file':('guide.txt',raw,'text/plain')},data={'metadata':json.dumps(meta)})
    result=upload();assert result.status_code==200,result.text
    doc=result.json();assert doc['status']=='draft' and not doc['external_approved']
    assert upload().json()['id']==doc['id']
    assert client.get('/api/knowledge/search',params={'q':'bearing guard'}).json()['items']==[]
    assert client.post('/api/knowledge/documents/'+doc['id']+'/review',json={'reason':'Reviewed fictional safety source','approve_external_public_processing':True}).status_code==422
    review=client.post('/api/knowledge/documents/'+doc['id']+'/review',json={'reason':'Reviewed fictional safety source'})
    assert review.status_code==200,review.text
    found=client.get('/api/knowledge/search',params={'q':'bearing guard'}).json()['items']
    assert len(found)==1 and found[0]['citation']['content_hash']
    source=client.get(found[0]['citation']['href']);assert source.status_code==200
    buyer=client.post('/api/auth/login',json={'role':'buyer','password':'corvo-demo'}).json()['access_token']
    headers={'Authorization':'Bearer '+buyer}
    assert client.get(found[0]['citation']['href'],headers=headers).status_code==404
    assert client.get('/api/knowledge/search',params={'q':'bearing guard'},headers=headers).json()['items']==[]

def test_index_idempotency_effective_policy_and_obsolete_sources(client):
    with api.Session.begin() as session:
        sync_core_sources(session)
        count=session.query(KnowledgeChunk).count();sync_core_sources(session)
        assert session.query(KnowledgeChunk).count()==count
        store_document(session,'synthetic-guide','old',[{'content':'obsolete cobalt guidance'}],metadata={'source_type':'guideline','visibility':'workspace'})
        store_document(session,'synthetic-guide','new',[{'content':'current copper guidance'}],metadata={'source_type':'guideline','visibility':'workspace'})
        store_document(session,'synthetic-guide','pending',[{'content':'draft zinc guidance'}],status='draft',metadata={'source_type':'guideline','visibility':'workspace'})
        store_document(session,'expired-guide','expired',[{'content':'expired cobalt guidance'}],metadata={'source_type':'guideline','visibility':'workspace','expires_at':'2020-01-01'})
    with api.Session() as session:
        assert not search(session,'admin','obsolete cobalt',api.business_today())
        assert search(session,'admin','current copper',api.business_today())
        assert not search(session,'admin','draft zinc',api.business_today())
        policy=search(session,'admin','emergency',api.business_today(),source_type='policy')
        assert policy and all(r['citation']['policy_version']=='5.0' for r in policy)
    with api.Session.begin() as session:
        store_document(session,'synthetic-guide','old',[{'content':'obsolete cobalt guidance'}],metadata={'source_type':'guideline','visibility':'workspace'})
        approved=list(session.query(KnowledgeDocument).filter_by(source_key='synthetic-guide',status='approved'))
        assert len(approved)==1 and approved[0].payload['title']=='old'

def test_tools_reject_write_and_preserve_auth(client):
    with pytest.raises(ValueError):execute(api.Session,'admin','approve_purchase_order',{})
    with pytest.raises(ValueError):execute(api.Session,'admin','get_master_item',{'item_code':'I-A','sql':'DROP TABLE users'})
    result=execute(api.Session,'admin','get_master_item',{'item_code':'I-A'})
    assert result['result']['item']['uom']=='NOS'
    with api.Session.begin() as session:sync_core_sources(session)
    clauses=execute(api.Session,'admin','search_policy_clauses',{'query':'emergency purchase limit'})['result']['matches']
    assert any('history_days' in entry['content'] for entry in clauses)

@pytest.mark.parametrize('value,expected',[('thirty',30),('two hundred and five',205),('1,500',1500),('two dozen',24)])
def test_spoken_quantities(value,expected):assert spoken_number(value)==Decimal(expected)

def test_hallucinated_fields_rejected_and_negative_model_cleared(data):
    plan=IntentPlan(intent='correct_purchase_request',updates={'quantity':'30','item_code':'I-C'},evidence={'quantity':'thirty','item_code':'bearing'})
    state,warnings=validate_updates({},plan,'thirty bearing',data)
    assert state['quantity']=='30' and not state.get('item_code') and warnings
    invented=IntentPlan(intent='create_purchase_request',updates={'plant':'P-A'},evidence={'plant':'P-A'})
    assert not validate_updates({},invented,'I need a bearing',data)[0].get('plant')
    state,_=validate_updates({'item_code':'I-A'},IntentPlan(intent='correct_purchase_request'),'not 6205-2RS',data)
    assert not state.get('item_code')
    pair_data=deepcopy(data);pair_data.items['I-A']['uom']='PAIR'
    omitted=IntentPlan(intent='create_purchase_request',updates={'quantity':'30','uom':'pairs'},evidence={'quantity':'thirty','uom':'pairs'})
    state,warnings=validate_updates({},omitted,'I need thirty pairs of I-A',pair_data)
    assert state['item_code']=='I-A' and state['quantity']=='30' and state['uom']=='PAIR' and not warnings
    spelled=IntentPlan(intent='create_purchase_request',updates={'quantity':'thirty'},evidence={'quantity':'thirty pairs of I-A by 2099-11-20'})
    assert validate_updates({},spelled,'Need thirty pairs of I-A by 2099-11-20',pair_data)[0]['quantity']=='30'
    state,_=validate_updates({},IntentPlan(intent='create_purchase_request'),'Need I-A and I-B',data)
    assert not state.get('item_code')

def test_grounding_rejects_unknown_citation_and_financial_invention():
    citations=[{'id':'real'}];evidence={'value':'100.00'}
    make=lambda text,ids:GroundedAnswer(answer=text,citation_ids=ids,insufficient_evidence=False,suggested_followups=[])
    assert not validate_answer(make('Value is 200',['real']),citations,evidence)
    assert not validate_answer(make('Value is 100',['invented']),citations,evidence)
    assert validate_answer(make('Value is 100.00',['real']),citations,evidence)

def test_budget_atomic_and_usage_has_no_prompt_content(client,monkeypatch):
    monkeypatch.setenv('CHAT_DAILY_TOKEN_LIMIT','1000')
    usage=reserve(api.Session,'admin',800,100,Decimal('.000001'),Decimal('.000002'),'mock')
    with pytest.raises(BudgetExceeded):reserve(api.Session,'admin',200,100,Decimal('.000001'),Decimal('.000002'),'mock')
    settle(api.Session,usage,10,5,Decimal('.000001'),Decimal('.000002'))
    with api.Session() as session:
        row=session.get(AIUsage,usage)
        assert row.cost_usd=='0.000020' and row.status=='completed'
        assert not any(k in row.payload for k in ['prompt','message','document'])

def test_google_float_embeddings_and_missing_usage_are_handled(client,monkeypatch):
    monkeypatch.setattr(safety,'isolated_demo',lambda:True)
    monkeypatch.setenv('AI_EXTERNAL_CALLS_ENABLED','true')
    monkeypatch.setenv('EXTERNAL_EMBEDDINGS_ENABLED','true')
    monkeypatch.setenv('GEMINI_API_KEY','fictional-test-key')
    def create(self,texts,task_type):
        assert task_type=='RETRIEVAL_DOCUMENT' and len(texts)==1
        return {'embeddings':[{'values':[.01]*1536}]}
    monkeypatch.setattr(Provider,'_embedding_request',create)
    vectors=Provider(api.Session,'admin').embed(['Entirely fictional public demo sentence'],safety.ExternalContext(True,('fictional_demo',),True))
    assert len(vectors[0])==1536
    assert abs(sum(v*v for v in vectors[0])-1)<1e-10
    with api.Session() as session:
        usage=session.query(AIUsage).one()
        assert usage.status=='completed' and usage.payload['token_count_estimated'] is True

def test_transient_gemini_retry_is_bounded_and_each_attempt_is_metered(client,monkeypatch):
    from contextlib import nullcontext
    monkeypatch.setattr(safety,'isolated_demo',lambda:True);monkeypatch.setenv('AI_EXTERNAL_CALLS_ENABLED','true');monkeypatch.setenv('GEMINI_API_KEY','fictional-test-key')
    calls=[]
    class Transient(Exception):status_code=503
    def create(**kwargs):
        assert api.engine.pool.checkedout()==0
        calls.append(kwargs)
        if len(calls)==1:raise Transient()
        return SimpleNamespace(model='mock',usage=SimpleNamespace(prompt_tokens=2,completion_tokens=3),choices=[SimpleNamespace(message=SimpleNamespace(content=IntentPlan(intent='create_purchase_request').model_dump_json()))])
    monkeypatch.setattr(Provider,'_client',lambda _:nullcontext(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))))
    result=Provider(api.Session,'admin').structured([{'role':'user','content':'Entirely fictional demo request'}],IntentPlan,safety.ExternalContext(True,('fictional_demo',),True))
    assert result.value.intent=='create_purchase_request' and len(calls)==2
    with api.Session() as session:assert sorted(r.status for r in session.query(AIUsage))==['completed','provider_error']

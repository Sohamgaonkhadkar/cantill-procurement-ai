from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import date,datetime,timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4
from typing import Annotated,Literal
import json,os,logging
from fastapi import FastAPI,Depends,HTTPException,UploadFile,File,Form,Query,Request
from fastapi.responses import Response,FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select,text
from sqlalchemy.exc import IntegrityError
from . import db
from .db import Policy,Run,Dataset,Contract,ContractLine,ContractProposal,RequirementRecord,PurchaseOrder,SourcingRequest,ContractLedger,Commitment,Override,Audit,Chat
from .db import User,PolicyApproval,PurchaseOrderLine,ChatMessage
from .domain import Data,read_csv,csv_bytes,INPUT_COLUMNS,digest,number,money,rate_text
from .engine import process,select_policy
from .policy import initial_policy,validate_policy,FACTS,OPS,ROUTES
from .ingest import pdf_text,extract_contract,validate_contract
from .service import current_data,execute_run,policies,audit,comparison,save_data
from .security import login,user,require,DEMO
from .suppliers import preferred
from .amendments import propose,field_diff
from .chat import parse_message
from .schemas import RunResponse,Page,LoginResponse,RequirementResponse,PolicyResponse,PolicyDefinition,ComparisonResponse,SimulationResponse,ActionResponse,ChatResponse

engine,Session=db.connect(); mutation_lock=RLock()
def business_today():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo('Asia/Kolkata')).date()
@asynccontextmanager
async def lifespan(app):
    # Vercel builds run migrations/bootstrap explicitly. Cold starts are read-only
    # with respect to schema and seeds, preventing DDL and insert races.
    if not os.getenv('VERCEL'):
        db.Base.metadata.create_all(engine)
        with Session.begin() as s:
            if not s.get(Policy,'5.0'): s.add(Policy(id='5.0',status='active',payload=initial_policy()))
            for role in ['requester','buyer','admin']:
                if not s.get(User,role): s.add(User(id=role,role=role,payload={'type':'controlled_demo_account','name':role.title()}))
    yield

app=FastAPI(title='Corvo Procurement OS API',version='1.0.0',lifespan=lifespan,
 description='Deterministic procurement, immutable runs and governed policy amendments. All business APIs require bearer authentication. Monetary values are decimal strings.')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000').split(','),allow_credentials=False,allow_methods=['GET','POST','PUT'],allow_headers=['Authorization','Content-Type'])

@app.exception_handler(ValueError)
async def value_error(_,exc): return JSONResponse(status_code=422,content={'error':{'code':'VALIDATION_ERROR','message':str(exc),'details':[]}})
@app.exception_handler(HTTPException)
async def http_error(_,exc): return JSONResponse(status_code=exc.status_code,content={'error':{'code':f'HTTP_{exc.status_code}','message':str(exc.detail),'details':[]}})
@app.exception_handler(RequestValidationError)
async def validation_error(_,exc): return JSONResponse(status_code=422,content={'error':{'code':'VALIDATION_ERROR','message':'Invalid request','details':json.loads(json.dumps(exc.errors(),default=str))}})
@app.exception_handler(IntegrityError)
async def integrity_error(_,exc):
    logging.getLogger('corvo').warning('Concurrent/duplicate write rejected')
    return JSONResponse(status_code=409,content={'error':{'code':'CONFLICT','message':'Record already exists or a referenced record is invalid','details':[]}})

class Body(BaseModel): model_config=ConfigDict(extra='forbid')
class LoginBody(Body):
    role:Literal['requester','buyer','admin']
    password:str
class PolicyBody(Body):
    policy:PolicyDefinition
    source_text:str=''
    base_version:str='5.0'
class Note(Body): reason:str=Field(min_length=5,max_length=2000)
class Simulation(Body): run_id:str
class OverrideBody(Note):
    route:Literal['RFQ','RFP','CAPEX_SOURCING','NEW_ITEM_SOURCING']
class ChatBody(Body):
    session_id:str|None=None
    message:str=Field(min_length=1,max_length=4000)
class ContractBody(Body):
    contract:dict
    reason:str=Field(min_length=5,max_length=2000)
class AmendmentTextBody(Body):
    text:str=Field(min_length=5,max_length=50000)
    version:str
    effective_date:date
    base_version:str='5.0'

def get(s,model,key):
    obj=s.get(model,key)
    if not obj: raise HTTPException(404,'Record not found')
    return obj
def page(items,offset,limit): return {'items':items[offset:offset+limit],'total':len(items),'offset':offset,'limit':limit}
async def content(file,extensions):
    if Path(file.filename or '').suffix.lower() not in extensions: raise ValueError('Unsupported file extension')
    value=await file.read(10*1024*1024+1)
    if len(value)>10*1024*1024: raise HTTPException(413,'Maximum upload size is 10 MiB')
    return value
def compact_run(r): return {k:r[k] for k in ['id','created_at','input_hash','data_hash','policy_hash','output_hash','status','counts','explicit_policy']}|{'line_count':len(r['rows']),'requirement_count':len(r['requirements']),'issue_count':len(r['issues'])}

@app.get('/health',tags=['System'])
def health():
    with Session() as s: s.execute(text('SELECT 1'))
    return {'status':'ok','database':'connected','demo_mode':DEMO}
@app.post('/api/auth/login',tags=['Authentication'],response_model=LoginResponse)
def sign_in(body:LoginBody): return {'access_token':login(body.role,body.password),'token_type':'bearer','role':body.role,'expires_in':28800}
@app.get('/api/auth/me',tags=['Authentication'])
def me(actor=Depends(user)): return {'id':actor,'role':actor,'demo_mode':DEMO}
@app.get('/api/overview',tags=['Overview'])
def overview(actor=Depends(user)):
    with Session() as s:
        runs=s.scalars(select(Run).order_by(Run.created_at.desc())).all(); reqs=s.scalars(select(RequirementRecord)).all()
        d=current_data(s)
        return {'items':len(d.items),'suppliers':len(d.suppliers),'contracts':len(d.contracts),'runs':len(runs),'pending_requirements':sum(r.payload['approval_status']=='pending' for r in reqs),'purchase_orders':len(s.scalars(select(PurchaseOrder)).all()),'sourcing_requests':len(s.scalars(select(SourcingRequest)).all()),'latest_run':compact_run(runs[0].payload) if runs else None}
@app.get('/api/master-data',tags=['Reference data'])
def masters(actor=Depends(user)):
    with Session() as s:
        d=current_data(s)
        return {'items':list(d.items.values()),'plants':list(d.plants.values()),'suppliers':list(d.suppliers.values())}

@app.post('/api/process-batch',tags=['Batch Lab'],response_model=RunResponse)
async def batch(file:UploadFile=File(...),policy_version:str|None=Form(None),actor=Depends(user)):
    rows=read_csv(await content(file,{'.csv'}),INPUT_COLUMNS)
    with Session.begin() as s: return execute_run(s,rows,policy_version or None,actor)
@app.get('/api/runs',tags=['Batch Lab'],response_model=Page)
def runs(offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),actor=Depends(user)):
    with Session() as s: return page([compact_run(r.payload) for r in s.scalars(select(Run).order_by(Run.created_at.desc()))],offset,limit)
@app.get('/api/runs/{run_id}',tags=['Batch Lab'],response_model=RunResponse)
def run_detail(run_id:str,actor=Depends(user)):
    with Session() as s: return get(s,Run,run_id).payload
@app.get('/api/runs/{run_id}/export.csv',tags=['Batch Lab'],response_class=Response,responses={200:{'content':{'text/csv':{'schema':{'type':'string'}}}}})
def run_export(run_id:str,actor=Depends(user)):
    with Session() as s: return Response(csv_bytes(get(s,Run,run_id).payload['rows']),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{run_id}.csv"'})
@app.post('/api/runs/{run_id}/replay',tags=['Batch Lab'])
def replay(run_id:str,actor=Depends(user)):
    with Session() as s:
        old=get(s,Run,run_id).payload; snapshot=get(s,Dataset,old['data_hash']).payload
        result=process(old['input'],Data(**snapshot),old['policy_snapshots'],old['explicit_policy'])
        return {'run_id':run_id,'matches':result['output_hash']==old['output_hash'],'output_hash':result['output_hash'],'result':result}
@app.get('/api/runs/{run_id}/compare/{other_id}',tags=['Batch Lab'],response_model=ComparisonResponse)
def compare(run_id:str,other_id:str,actor=Depends(user)):
    with Session() as s: return comparison(get(s,Run,run_id).payload,get(s,Run,other_id).payload)

@app.get('/api/requirements',tags=['Buyer Inbox'],response_model=Page)
def requirements(run_id:str|None=None,route:str|None=None,status:str|None=None,search:str='',offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),actor=Depends(user)):
    with Session() as s:
        stmt=select(RequirementRecord)
        if run_id: stmt=stmt.where(RequirementRecord.run_id==run_id)
        rows=[dict(r.payload,record_id=r.id,run_id=r.run_id) for r in s.scalars(stmt)]
        rows=[r for r in rows if (not route or r['route']==route) and (not status or r['approval_status']==status) and search.lower() in (r['description']+' '+r['item_code']+' '+r['plant']).lower()]
        return page(sorted(rows,key=lambda r:(r['created_at'],r['record_id'])),offset,limit)
@app.get('/api/requirements/{requirement_id}',tags=['Decision Trace'],response_model=RequirementResponse)
def requirement_detail(requirement_id:str,run_id:str,actor=Depends(user)):
    with Session() as s:
        r=get(s,RequirementRecord,run_id+':'+requirement_id)
        return dict(r.payload,record_id=r.id,run_id=run_id)

@app.get('/api/policy-schema',tags=['Policy Studio'])
def policy_schema(actor=Depends(user)):
    return {'facts':{k:v.__name__ for k,v in FACTS.items()},'operators':sorted(OPS),'boolean_operators':['all','any','not'],'routes':sorted(ROUTES),'example':initial_policy()}
@app.get('/api/policies',tags=['Policy Studio'])
def list_policies(actor=Depends(user)):
    with Session() as s: return {'items':[{**r.payload,'status':r.status,'id':r.id} for r in s.scalars(select(Policy))]}
def new_policy(s,body,actor):
    policy=validate_policy(body.policy.model_dump(by_alias=True))
    if s.get(Policy,policy['version']): raise HTTPException(409,'Policy version already exists')
    base=get(s,Policy,body.base_version)
    payload={**policy,'governance':{'base_version':body.base_version,'source_text':body.source_text,'proposed_by':actor,'proposed_at':db.now(),'reviewed':False,'diff':field_diff(base.payload,policy)}}
    s.add(Policy(id=policy['version'],status='draft',payload=payload)); audit(s,actor,'policy.proposed',{'version':policy['version']})
    return {**payload,'status':'draft','id':policy['version']}
@app.post('/api/policies',tags=['Policy Studio'],response_model=PolicyResponse)
def create_policy(body:PolicyBody,actor=Depends(user)):
    require(actor,'admin')
    with Session.begin() as s: return new_policy(s,body,actor)
@app.post('/api/policies/propose-amendment',tags=['Policy Studio'],response_model=PolicyResponse)
def text_amendment(body:AmendmentTextBody,actor=Depends(user)):
    require(actor,'admin')
    with Session.begin() as s:
        base=deepcopy(get(s,Policy,body.base_version).payload); base.pop('governance',None)
        p,detected=propose(base,body.text,body.version,body.effective_date.isoformat())
        result=new_policy(s,PolicyBody(policy=p,source_text=body.text,base_version=body.base_version),actor)
        return {**result,'interpretation':{'detected_changes':detected,'requires_manual_review':True,'warning':'Review structured rules against the entire source; unsupported clauses require manual editing.'}}
@app.put('/api/policies/{policy_id}',tags=['Policy Studio'],response_model=PolicyResponse)
def edit_policy(policy_id:str,body:PolicyBody,actor=Depends(user)):
    require(actor,'admin')
    with Session.begin() as s:
        r=get(s,Policy,policy_id)
        if r.status!='draft': raise HTTPException(409,'Approved policy snapshots are immutable')
        p=validate_policy(body.policy.model_dump(by_alias=True))
        if p['version']!=policy_id: raise ValueError('Cannot rename policy version')
        base=get(s,Policy,body.base_version)
        r.payload={**p,'governance':{**r.payload.get('governance',{}),'source_text':body.source_text,'base_version':body.base_version,'reviewed':False,'diff':field_diff(base.payload,p)}}
        audit(s,actor,'policy.edited',{'version':policy_id})
        return {**r.payload,'status':r.status,'id':r.id}
@app.post('/api/policies/upload-amendment',tags=['Policy Studio'],response_model=PolicyResponse)
async def upload_amendment(file:UploadFile=File(...),version:str=Form(...),effective_date:str=Form(...),base_version:str=Form('5.0'),actor=Depends(user)):
    require(actor,'admin'); raw=await content(file,{'.pdf','.txt','.json'})
    text_source=pdf_text(raw) if file.filename.lower().endswith('.pdf') else raw.decode('utf-8-sig')
    with Session.begin() as s:
        base=deepcopy(get(s,Policy,base_version).payload); base.pop('governance',None)
        if file.filename.lower().endswith('.json'):
            p=json.loads(text_source); p['version']=version; p['effective_date']=effective_date; detected=['Structured policy document loaded']
        else: p,detected=propose(base,text_source,version,effective_date)
        result=new_policy(s,PolicyBody(policy=p,source_text=text_source,base_version=base_version),actor)
        return {**result,'interpretation':{'detected_changes':detected,'requires_manual_review':True,'warning':'Conservative extraction: compare every clause to the source; use the rule editor for unsupported language. PDF signatures are not cryptographically verified.'}}
@app.post('/api/policies/{policy_id}/review',tags=['Policy Studio'],response_model=PolicyResponse)
def review_policy(policy_id:str,body:Note,actor=Depends(user)):
    require(actor,'admin')
    with Session.begin() as s:
        p=get(s,Policy,policy_id)
        if p.status!='draft': raise HTTPException(409,'Only drafts can be reviewed')
        p.payload={**p.payload,'governance':{**p.payload.get('governance',{}),'reviewed':True,'review_note':body.reason,'reviewed_by':actor,'reviewed_at':db.now()}}
        audit(s,actor,'policy.reviewed',{'version':policy_id,'reason':body.reason})
        return {**p.payload,'id':p.id,'status':p.status}
@app.post('/api/policies/{policy_id}/approve',tags=['Policy Studio'],response_model=PolicyResponse)
def approve_policy(policy_id:str,body:Note,actor=Depends(user)):
    require(actor,'admin')
    with Session.begin() as s:
        p=get(s,Policy,policy_id)
        if p.status!='draft' or not p.payload.get('governance',{}).get('reviewed'): raise HTTPException(409,'Review this draft before approval')
        validate_policy(p.payload); p.status='approved'
        p.payload={**p.payload,'governance':{**p.payload['governance'],'approved_by':actor,'approved_at':db.now(),'approval_reason':body.reason,'snapshot_hash':digest(p.payload)}}
        s.add(PolicyApproval(id='APPROVAL-'+uuid4().hex,policy_id=policy_id,payload={'actor':actor,'timestamp':db.now(),'reason':body.reason,'snapshot_hash':digest(p.payload)}))
        audit(s,actor,'policy.approved',{'version':policy_id,'reason':body.reason})
        return {**p.payload,'id':p.id,'status':p.status}
@app.post('/api/policies/{policy_id}/activate',tags=['Policy Studio'])
def activate_policy(policy_id:str,body:Note,actor=Depends(user)):
    require(actor,'admin')
    with Session.begin() as s:
        p=get(s,Policy,policy_id)
        if p.status not in {'approved','superseded','active'}: raise HTTPException(409,'Approve policy first')
        p.status='active'; audit(s,actor,'policy.activation_scheduled',{'version':policy_id,'effective_date':p.payload['effective_date'],'reason':body.reason})
        return {'id':p.id,'status':'active','effective_date':p.payload['effective_date'],'scheduled':p.payload['effective_date']>business_today().isoformat()}
@app.post('/api/policies/{policy_id}/simulate',tags=['Policy Studio'],response_model=SimulationResponse)
def simulate_policy(policy_id:str,body:Simulation,actor=Depends(user)):
    require(actor,'admin','buyer')
    with Session() as s:
        old=get(s,Run,body.run_id).payload; p=get(s,Policy,policy_id)
        snapshot=Data(**get(s,Dataset,old['data_hash']).payload)
        # Draft is allowed only in an explicitly labeled non-persisting simulation.
        ps=[x for x in old['policy_snapshots'] if x['version']!=policy_id]+[{**p.payload,'status':'active'}]
        new=process(old['input'],snapshot,ps,policy_id)
        return {'simulation':True,'policy_id':policy_id,'base_run_id':body.run_id,'result':new,'comparison':comparison(old,new)}
@app.post('/api/policies/{policy_id}/deactivate',tags=['Policy Studio'])
def deactivate_policy(policy_id:str,body:Note,actor=Depends(user)):
    require(actor,'admin')
    with Session.begin() as s:
        p=get(s,Policy,policy_id)
        if p.status!='active': raise HTTPException(409,'Only active policies can be deactivated')
        p.status='superseded'
        audit(s,actor,'policy.deactivated',{'version':policy_id,'reason':body.reason})
        return {'id':p.id,'status':p.status,'explicit_historical_runs_available':True}
@app.post('/api/policies/preview',tags=['Policy Studio'])
def preview_policy(body:PolicyBody,actor=Depends(user)):
    require(actor,'admin','buyer'); p=validate_policy(body.policy.model_dump(by_alias=True))
    with Session() as s: return {'valid':True,'diff':field_diff(get(s,Policy,body.base_version).payload,p),'policy':p,'snapshot_hash':digest(p)}

@app.get('/api/preferred-suppliers',tags=['Supplier Intelligence'],response_model=Page)
def preferred_suppliers(as_of:date,item_code:str|None=None,policy_version:str|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=500),actor=Depends(user)):
    with Session() as s:
        d=current_data(s); p=select_policy(policies(s),as_of,policy_version)
        if item_code and item_code not in d.items: raise HTTPException(404,'Unknown item')
        rows=[]
        for item in sorted([item_code] if item_code else d.items):
            for rank,r in enumerate(preferred(d,item,as_of,p),1): rows.append({'item_code':item,'rank':rank,**r})
        return {**page(rows,offset,limit),'as_of':as_of.isoformat(),'policy_version':p['version']}
@app.get('/api/preferred-suppliers/export.csv',tags=['Supplier Intelligence'],response_class=Response,responses={200:{'content':{'text/csv':{'schema':{'type':'string'}}}}})
def preferred_export(as_of:date,policy_version:str|None=None,actor=Depends(user)):
    with Session() as s:
        d=current_data(s); p=select_policy(policies(s),as_of,policy_version); rows=[]
        for item in sorted(d.items):
            for rank,r in enumerate(preferred(d,item,as_of,p)[:p['parameters']['preferred_count']],1): rows.append({'item_code':item,'rank':rank,'supplier_id':r['supplier_id'],'reference_price':rate_text(r['reference_price'])})
        return Response(csv_bytes(rows,['item_code','rank','supplier_id','reference_price']),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="preferred.csv"'})

@app.get('/api/contracts',tags=['Contract Vault'],response_model=Page)
def contracts(as_of:date|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),actor=Depends(user)):
    with Session() as s:
        d=current_data(s); rows=[]; day=(as_of or business_today()).isoformat()
        for c in sorted(d.contracts,key=lambda x:x['contract_id']):
            committed=sum((number(l.payload['amount']) for l in s.scalars(select(ContractLedger).where(ContractLedger.contract_id==c['contract_id']))),number(0))
            rows.append({**c,'committed_value':str(committed),'remaining_value':str(number(c['value_cap'])-number(c['consumed_value'])),'supplier_status':d.suppliers[c['supplier_id']]['status'],'valid_as_of':c['start_date']<=day<=c['end_date']})
        return {**page(rows,offset,limit),'as_of':day}
@app.post('/api/contracts/upload',tags=['Contract Vault'])
async def upload_contract(file:UploadFile=File(...),actor=Depends(user)):
    require(actor,'admin','buyer'); raw=await content(file,{'.pdf'}); source=pdf_text(raw)
    try: proposed=extract_contract(raw); error=None
    except ValueError as exc: proposed=None; error=str(exc)
    proposal_id='CP-'+uuid4().hex
    with Session.begin() as s:
        if proposed:
            try: validate_contract(proposed,current_data(s))
            except ValueError as exc: error=str(exc)
        payload={'id':proposal_id,'status':'pending_review','contract':proposed,'source_text':source,'source_hash':digest(source),'validation_error':error,'signature_verified':False,'actor':actor}
        s.add(ContractProposal(id=proposal_id,payload=payload)); audit(s,actor,'contract.uploaded',{'proposal_id':proposal_id,'source_hash':digest(source)})
        return payload
@app.get('/api/contracts/proposals',tags=['Contract Vault'])
def contract_proposals(actor=Depends(user)):
    require(actor,'admin','buyer')
    with Session() as s: return {'items':[r.payload for r in s.scalars(select(ContractProposal))]}
@app.post('/api/contracts/proposals/{proposal_id}/approve',tags=['Contract Vault'])
def approve_contract(proposal_id:str,body:ContractBody,actor=Depends(user)):
    require(actor,'admin','buyer')
    with mutation_lock,Session.begin() as s:
        proposal=get(s,ContractProposal,proposal_id)
        if proposal.payload['status']!='pending_review': raise HTTPException(409,'Proposal already approved')
        c=validate_contract(deepcopy(body.contract),current_data(s))
        if s.get(Contract,c['contract_id']): raise HTTPException(409,'Contract ID already exists; resolve conflicting authoritative records privately')
        c['provenance']={'type':'buyer_verified_pdf','source_hash':proposal.payload['source_hash'],'extracted_text':proposal.payload['source_text'],'verified_by':actor,'verified_at':db.now(),'reason':body.reason,'signature_verified':False}
        s.add(Contract(id=c['contract_id'],supplier_id=c['supplier_id'],payload=c)); s.flush()
        for line in c['lines']: s.add(ContractLine(id=c['contract_id']+':'+line['item_code'],contract_id=c['contract_id'],item_id=line['item_code'],payload=line))
        proposal.payload={**proposal.payload,'status':'approved','approved_contract_id':c['contract_id']}
        audit(s,actor,'contract.approved',{'proposal_id':proposal_id,'contract_id':c['contract_id'],'reason':body.reason})
        return c

def commit_requirement(s,run_id,requirement_id,actor,reason):
    # Lock contracts in a stable order. PostgreSQL row locks serialize concurrent
    # approvals across processes; the local lock covers the SQLite demo process.
    s.scalars(select(Contract).order_by(Contract.id).with_for_update()).all()
    r=get(s,RequirementRecord,run_id+':'+requirement_id)
    if r.payload['approval_status']!='pending': raise HTTPException(409,'Requirement already actioned')
    target=r.payload
    if target['route']=='NOT_PROCESSED': raise HTTPException(409,'Invalid requirement cannot be approved')
    records=[r]
    if target['po_id']:
        records=[x for x in s.scalars(select(RequirementRecord).where(RequirementRecord.run_id==run_id)) if x.payload['po_id']==target['po_id'] and x.payload['approval_status']=='pending']
    action_id=target['po_id'] or 'SRC-'+digest([run_id,requirement_id])[:16]
    d=current_data(s)
    for record in records:
        rec=record.payload
        for line in rec['lines']:
            key=digest([line['pr_no'],line['pr_line']])
            if s.get(Commitment,key): raise HTTPException(409,'A PR line has already been approved in another run')
            s.add(Commitment(id=key,action_id=action_id))
        if rec['supplier_id'] and d.suppliers.get(rec['supplier_id'],{}).get('status')!='Active': raise HTTPException(409,'Supplier is no longer Active')
        cid=rec['evidence'].get('selected_contract')
        if cid:
            c=get(s,Contract,cid).payload
            actual=next((l for l in c['lines'] if l['item_code']==rec['item_code']),None)
            if not actual or number(actual['rate'])!=number(rec['unit_price']): raise HTTPException(409,'Contract rate changed; reprocess batch')
            amount=number(rec['quantity'])*number(actual['rate'])
            committed=sum((number(x.payload['amount']) for x in s.scalars(select(ContractLedger).where(ContractLedger.contract_id==cid))),number(0))
            if number(c['consumed_value'])+committed+amount>number(c['value_cap']): raise HTTPException(409,'Contract headroom changed; reprocess batch')
            s.add(ContractLedger(id=run_id+':'+record.group_id,contract_id=cid,payload={'amount':str(amount),'action_id':action_id,'actor':actor,'timestamp':db.now()})); s.flush()
        record.payload={**rec,'approval_status':'approved','approved_by':actor,'approved_at':db.now(),'action_id':action_id}
    payload={'id':action_id,'run_id':run_id,'requirements':[x.group_id for x in records],'recommendations':[x.payload for x in records],'actor':actor,'approved_at':db.now(),'reason':reason,'status':'approved'}
    if target['decision']=='PO':
        s.add(PurchaseOrder(id=action_id,run_id=run_id,supplier_id=target['supplier_id'],payload=payload)); s.flush()
        for record in records: s.add(PurchaseOrderLine(id=action_id+':'+record.group_id,order_id=action_id,requirement_id=record.id,payload=record.payload))
    else: s.add(SourcingRequest(id=action_id,run_id=run_id,payload=payload))
    audit(s,actor,'purchase_order.approved' if target['decision']=='PO' else 'sourcing.approved',{'id':action_id,'run_id':run_id,'requirements':payload['requirements'],'reason':reason})
    return payload

@app.post('/api/requirements/{requirement_id}/approve',tags=['Buyer Inbox'],response_model=ActionResponse)
def approve_requirement(requirement_id:str,body:Note,run_id:str,actor=Depends(user)):
    require(actor,'buyer','admin')
    with mutation_lock,Session.begin() as s: return commit_requirement(s,run_id,requirement_id,actor,body.reason)
@app.post('/api/requirements/{requirement_id}/override',tags=['Buyer Inbox'],response_model=ActionResponse)
def override_requirement(requirement_id:str,body:OverrideBody,run_id:str,actor=Depends(user)):
    require(actor,'buyer','admin')
    with mutation_lock,Session.begin() as s:
        r=get(s,RequirementRecord,run_id+':'+requirement_id)
        if r.payload['approval_status']!='pending': raise HTTPException(409,'Requirement already actioned')
        original=deepcopy(r.payload); oid='OVR-'+uuid4().hex
        for line in original['lines']:
            key=digest([line['pr_no'],line['pr_line']])
            if s.get(Commitment,key): raise HTTPException(409,'PR line already approved')
            s.add(Commitment(id=key,action_id=oid))
        r.payload={**r.payload,'approval_status':'overridden','override_id':oid}
        final={**original,'route':body.route,'decision':'SOURCING_REQUEST','supplier_id':'','unit_price':'','po_id':''}
        payload={'id':oid,'run_id':run_id,'requirements':[requirement_id],'recommendations':[final],'actor':actor,'approved_at':db.now(),'reason':body.reason,'status':'approved'}
        s.add(SourcingRequest(id=oid,run_id=run_id,payload=payload)); s.add(Override(id=oid,payload={'original':original,'final':final,'actor':actor,'reason':body.reason,'created_at':db.now()}))
        audit(s,actor,'requirement.overridden',{'id':oid,'run_id':run_id,'requirement_id':requirement_id,'original_route':original['route'],'final_route':body.route,'reason':body.reason})
        return payload

@app.get('/api/purchase-orders',tags=['Purchase Orders'],response_model=Page)
def purchase_orders(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),actor=Depends(user)):
    with Session() as s: return page([r.payload for r in s.scalars(select(PurchaseOrder).order_by(PurchaseOrder.id))],offset,limit)
@app.get('/api/purchase-orders/{order_id}',tags=['Purchase Orders'])
def purchase_order(order_id:str,actor=Depends(user)):
    with Session() as s: return get(s,PurchaseOrder,order_id).payload
@app.get('/api/sourcing',tags=['Sourcing'],response_model=Page)
def sourcing(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),actor=Depends(user)):
    with Session() as s: return page([r.payload for r in s.scalars(select(SourcingRequest).order_by(SourcingRequest.id))],offset,limit)
@app.get('/api/sourcing/{sourcing_id}',tags=['Sourcing'])
def sourcing_detail(sourcing_id:str,actor=Depends(user)):
    with Session() as s: return get(s,SourcingRequest,sourcing_id).payload
@app.get('/api/audit',tags=['Audit Trail'],response_model=Page)
def audit_events(action:str|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),actor=Depends(user)):
    require(actor,'buyer','admin')
    with Session() as s:
        rows=[{'id':r.id,'created_at':r.created_at,**r.payload} for r in s.scalars(select(Audit).order_by(Audit.created_at.desc(),Audit.id))]
        return page([r for r in rows if not action or r['action']==action],offset,limit)

@app.post('/api/chat/messages',tags=['Request Desk'],response_model=ChatResponse)
def chat_message(body:ChatBody,actor=Depends(user)):
    from zoneinfo import ZoneInfo
    with mutation_lock,Session.begin() as s:
        session_id=body.session_id or 'CHAT-'+uuid4().hex
        record=s.get(Chat,session_id)
        if body.session_id and not record: raise HTTPException(404,'Chat session not found')
        payload=deepcopy(record.payload) if record else {'actor':actor,'messages':[],'state':{}}
        if payload['actor']!=actor: raise HTTPException(403,'This session belongs to another actor')
        payload['messages'].append({'role':'user','content':body.message,'timestamp':db.now()})
        result=None
        if body.message.strip().lower() in {'confirm','yes','submit'} and payload['state'].get('ready'):
            state=payload['state']; item=current_data(s).items.get(state['item_code'],{})
            created=datetime.now(ZoneInfo('Asia/Kolkata')).replace(tzinfo=None).isoformat(timespec='seconds')
            row={'pr_no':'PR-CHAT-'+session_id[-12:].upper(),'pr_line':'1','created_at':created,'requester':actor,'department':'Chat intake','plant':state['plant'],'item_code':'' if state['item_code']=='NEW' else state['item_code'],'description':item.get('description',state['description']),'quantity':state['quantity'],'uom':state['uom'],'estimated_unit_price':state.get('estimated_unit_price',''),'need_by_date':state['need_by_date'],'urgency':state['urgency']}
            result=execute_run(s,[row],None,actor)
            if result['issues']: reply='Request validation failed: '+str(result['issues'])
            else: reply='PR created. '+result['rows'][0]['reason']; payload['state']={}
        else:
            state,reply=parse_message(payload['state'],body.message,current_data(s)); payload['state']=state
        payload['messages'].append({'role':'assistant','content':reply,'timestamp':db.now()})
        if record: record.payload=payload
        else: s.add(Chat(id=session_id,payload=payload))
        s.flush()
        for message in payload['messages'][-2:]: s.add(ChatMessage(id=uuid4().hex,chat_id=session_id,payload=message))
        audit(s,actor,'chat.message',{'session_id':session_id,'pr_created':bool(result and not result['issues'])})
        return {'session_id':session_id,'message':reply,'state':payload['state'],'alternatives':payload['state'].get('alternatives',[]),'run':result,'messages':payload['messages']}
@app.get('/api/chat/sessions/{session_id}',tags=['Request Desk'])
def chat_session(session_id:str,actor=Depends(user)):
    with Session() as s:
        r=get(s,Chat,session_id)
        if r.payload['actor']!=actor: raise HTTPException(403,'This session belongs to another actor')
        return {'session_id':session_id,**r.payload}

@app.get('/',include_in_schema=False)
def index():
    root=Path(__file__).parent.parent
    built=root/'frontend'/'dist'/'index.html'
    return FileResponse(built if built.is_file() else root/'frontend'/'index.html')

@app.post('/api/admin/import-data',tags=['Private Administration'])
async def import_data(file:UploadFile=File(...),actor=Depends(user)):
    from io import BytesIO
    from pathlib import PurePosixPath
    import tempfile,zipfile
    from .ingest import load_kit
    require(actor,'admin'); raw=await content(file,{'.zip'})
    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive,tempfile.TemporaryDirectory(prefix='corvo-import-') as temp:
            infos=archive.infolist()
            if len(infos)>250 or sum(i.file_size for i in infos)>50*1024*1024: raise ValueError('Archive exceeds import limits')
            for info in infos:
                path=PurePosixPath(info.filename.replace('\\','/'))
                if path.is_absolute() or '..' in path.parts or ':' in str(path): raise ValueError('Unsafe archive path')
                if info.is_dir(): continue
                if path.suffix.lower() not in {'.csv','.pdf','.txt'}: raise ValueError('Unsupported archive content')
                target=Path(temp).joinpath(*path.parts)
                target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(archive.read(info))
            roots=list(Path(temp).rglob('item_master.csv'))
            if len(roots)!=1: raise ValueError('Expected exactly one master_data/item_master.csv')
            data=load_kit(roots[0].parent.parent)
            with mutation_lock,Session.begin() as s:
                if s.scalars(select(Commitment)).first(): raise HTTPException(409,'Cannot replace master data after purchasing commitments; use a separate database')
                snapshot=save_data(s,data); audit(s,actor,'data.imported',{'snapshot':snapshot,'items':len(data.items),'contracts':len(data.contracts)})
                return {'snapshot_id':snapshot,'items':len(data.items),'suppliers':len(data.suppliers),'history_rows':len(data.history),'contracts':len(data.contracts)}
    except zipfile.BadZipFile as exc: raise ValueError('Invalid ZIP archive') from exc

def custom_openapi():
    from fastapi.openapi.utils import get_openapi
    if app.openapi_schema: return app.openapi_schema
    schema=get_openapi(title=app.title,version=app.version,description=app.description,routes=app.routes)
    schema['components']['schemas']['ErrorResponse']={'type':'object','required':['error'],'properties':{'error':{'type':'object','required':['code','message','details'],'properties':{'code':{'type':'string'},'message':{'type':'string'},'details':{'type':'array','items':{}}}}}}
    for path,methods in schema['paths'].items():
        for method,operation in methods.items():
            if method not in {'get','post','put','delete','patch'}: continue
            statuses=[422,409,413] if method in {'post','put'} else [422]
            if path.startswith('/api/') and path!='/api/auth/login': statuses += [401,403,404]
            if path=='/api/auth/login': statuses += [401]
            for status in statuses:
                operation.setdefault('responses',{})[str(status)]={'description':{401:'Sign-in required or invalid credentials',403:'Role not permitted',404:'Record not found',409:'Conflicting action or record',413:'Upload too large',422:'Validation failed'}[status],'content':{'application/json':{'schema':{'$ref':'#/components/schemas/ErrorResponse'}}}}
    app.openapi_schema=schema
    return schema
app.openapi=custom_openapi

@app.get('/{frontend_path:path}',include_in_schema=False)
def frontend_route(frontend_path:str,request:Request):
    # In production Vercel serves public assets from its CDN. This fallback also
    # supports a single Docker image with a built Arena SPA.
    if frontend_path.startswith('api/'):
        from starlette.routing import Match
        if any(route.matches(request.scope)[0]==Match.PARTIAL for route in app.routes): raise HTTPException(405,'Method not allowed')
        raise HTTPException(404,'API route not found')
    root=(Path(__file__).parent.parent/'frontend'/'dist').resolve()
    candidate=(root/frontend_path).resolve()
    if candidate.is_relative_to(root) and candidate.is_file(): return FileResponse(candidate)
    if (root/'index.html').is_file(): return FileResponse(root/'index.html')
    raise HTTPException(404,'Arena frontend has not been integrated')

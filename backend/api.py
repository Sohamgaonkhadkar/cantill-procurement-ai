from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import date,datetime,timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4
from typing import Annotated,Literal
import json,os,logging,hashlib
from fastapi import FastAPI,Depends,HTTPException,UploadFile,File,Form,Query,Request
from fastapi.responses import Response,FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select,text,func,or_
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from . import db
from .db import Policy,Run,Dataset,Contract,ContractLine,ContractProposal,RequirementRecord,PurchaseOrder,SourcingRequest,ContractLedger,Commitment,Override,Audit,Chat
from .db import User,PolicyApproval,PurchaseOrderLine,ChatMessage,AuthSession
from .domain import Data,read_csv,csv_bytes,INPUT_COLUMNS,digest,number,money,rate_text
from .engine import process,select_policy
from .policy import initial_policy,validate_policy,FACTS,OPS,ROUTES
from .ingest import pdf_text,extract_contract,validate_contract
from .service import current_data,execute_run,policies,audit,comparison,save_data
from .security import authenticate,user,require,require_owner,DEMO,configure_sessions,role_of,hash_password,submission_access,registration_enabled,SUBMISSION_PASSWORDS,ROLES
from .suppliers import preferred
from .amendments import policy_diff as field_diff
from .language import interpret
from .chat import parse_message
from .security import consume_rate_limit
from .schemas import RunResponse,Page,LoginResponse,RequirementResponse,PolicyResponse,PolicyDefinition,ComparisonResponse,SimulationResponse,ActionResponse,ChatResponse,ProcessingResult

engine,Session=db.connect(); mutation_lock=RLock()
configure_sessions(lambda:Session)
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
app.add_middleware(CORSMiddleware,allow_origins=[origin.strip() for origin in os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000').split(',') if origin.strip()],allow_credentials=False,allow_methods=['GET','POST','PUT'],allow_headers=['Authorization','Content-Type'])

@app.exception_handler(ValueError)
async def value_error(_,exc): return JSONResponse(status_code=422,content={'error':{'code':'VALIDATION_ERROR','message':str(exc),'details':[]}})
@app.exception_handler(HTTPException)
async def http_error(_,exc): return JSONResponse(status_code=exc.status_code,headers=exc.headers,content={'error':{'code':f'HTTP_{exc.status_code}','message':str(exc.detail),'details':[]}})
@app.exception_handler(RequestValidationError)
async def validation_error(_,exc): return JSONResponse(status_code=422,content={'error':{'code':'VALIDATION_ERROR','message':'Invalid request','details':[{k:error[k] for k in ['loc','msg','type']} for error in exc.errors()]}})
@app.exception_handler(IntegrityError)
async def integrity_error(_,exc):
    logging.getLogger('corvo').warning('Concurrent/duplicate write rejected')
    return JSONResponse(status_code=409,content={'error':{'code':'CONFLICT','message':'Record already exists or a referenced record is invalid','details':[]}})
@app.exception_handler(SQLAlchemyError)
async def database_error(_,exc):
    logging.getLogger('corvo').warning('Database operation unavailable: %s',type(exc).__name__)
    return JSONResponse(status_code=503,headers={'Retry-After':'5'},content={'error':{'code':'SERVICE_UNAVAILABLE','message':'Database temporarily unavailable; retry the operation','details':[]}})

class Body(BaseModel): model_config=ConfigDict(extra='forbid')
class LoginBody(Body):
    role:Literal['requester','buyer','admin']|None=None
    username:str|None=Field(None,min_length=3,max_length=64)
    password:str=Field(min_length=1,max_length=128)
class CreateUserBody(Body):
    username:str=Field(pattern=r'^[a-z][a-z0-9._-]{2,63}$')
    display_name:str=Field(min_length=1,max_length=100)
    role:Literal['requester','buyer','admin']
    password:str=Field(min_length=15,max_length=128)
    access_scope:Literal['standard','evaluation']='standard'
class RegisterBody(Body):
    username:str=Field(pattern=r'^[a-z][a-z0-9._-]{2,63}$')
    display_name:str=Field(min_length=1,max_length=100)
    password:str=Field(min_length=15,max_length=128)
class PublicRole(Body):
    role:Literal['requester','buyer','admin']
    password:str
class AuthOptions(Body):
    submission_access:bool
    registration_enabled:bool
    roles:list[PublicRole]
class DemoPreviewResponse(Body):
    mode:Literal['synthetic_preview']='synthetic_preview'
    persistent:Literal[False]=False
    policy_version:Literal['5.0']='5.0'
    source_note:str
    result:ProcessingResult
class PolicyBody(Body):
    policy:PolicyDefinition
    source_text:str=''
    base_version:str='5.0'
class Note(Body): reason:str=Field(min_length=5,max_length=2000)
class PolicyReviewBody(Note): manual_verification:bool=False
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

def get(s,model,key,lock=False):
    obj=s.scalar(select(model).where(model.id==key).with_for_update()) if lock else s.get(model,key)
    if not obj: raise HTTPException(404,'Record not found')
    return obj
def page(items,offset,limit): return {'items':items[offset:offset+limit],'total':len(items),'offset':offset,'limit':limit}
def database_page(s,statement,offset,limit,mapper=lambda row:row.payload):
    total=s.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    return {'items':[mapper(row) for row in s.scalars(statement.offset(offset).limit(limit))],'total':total,'offset':offset,'limit':limit}
async def content(file,extensions):
    if Path(file.filename or '').suffix.lower() not in extensions: raise ValueError('Unsupported file extension')
    value=await file.read(10*1024*1024+1)
    if len(value)>10*1024*1024: raise HTTPException(413,'Maximum upload size is 10 MiB')
    return value
def compact_run(r): return {k:r[k] for k in ['id','created_at','input_hash','data_hash','policy_hash','output_hash','status','counts','explicit_policy']}|{'line_count':len(r['rows']),'requirement_count':len(r['requirements']),'issue_count':len(r['issues'])}
def accessible_run(s,run_id,actor):
    run=get(s,Run,run_id)
    if role_of(actor)=='requester' and run.payload['actor']!=str(actor): raise HTTPException(404,'Record not found')
    return run
def run_query(actor):
    statement=select(Run)
    if role_of(actor)=='requester': statement=statement.where(Run.payload['actor'].as_string()==str(actor))
    return statement

@app.get('/health',tags=['System'])
def health():
    with Session() as s: s.execute(text('SELECT 1'))
    return {'status':'ok','database':'connected','demo_mode':DEMO}
@app.post('/api/auth/login',tags=['Authentication'],response_model=LoginResponse)
def sign_in(body:LoginBody):
    if bool(body.username)==bool(body.role): raise ValueError('Supply exactly one of username or role')
    return authenticate(body.username or body.role,body.password)
@app.get('/api/auth/options',tags=['Authentication'],response_model=AuthOptions)
def auth_options():
    enabled=submission_access()
    return {'submission_access':enabled,'registration_enabled':registration_enabled(),'roles':[{'role':role,'password':password} for role,password in SUBMISSION_PASSWORDS.items()] if enabled else []}

@app.post('/api/auth/register',tags=['Authentication'],response_model=LoginResponse,status_code=201)
def register(body:RegisterBody,request:Request):
    if not registration_enabled(): raise HTTPException(403,'Self-registration is disabled')
    # Requester-only registration, with an atomic persistent per-address quota.
    # Never accept a role from this public endpoint.
    from .db import AuthThrottle
    import time
    now=int(time.time())
    key=hashlib.sha256(('registration:'+str(request.client.host if request.client else 'unknown')).encode()).hexdigest()
    limited=False
    with Session.begin() as s:
        if s.bind.dialect.name=='postgresql':
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        s.execute(insert(AuthThrottle).values(id=key,failures=0,window_started=now).on_conflict_do_nothing(index_elements=['id']))
        throttle=s.scalar(select(AuthThrottle).where(AuthThrottle.id==key).with_for_update())
        if now-throttle.window_started>=900: throttle.failures=0; throttle.window_started=now
        if throttle.failures>=5: limited=True
        else: throttle.failures+=1
        delay=max(1,900-(now-throttle.window_started))
    if limited: raise HTTPException(429,'Too many account creation attempts; retry later',headers={'Retry-After':str(delay)})
    with Session.begin() as s:
        if body.username in ROLES or s.get(User,body.username): raise HTTPException(409,'Username already exists')
        s.add(User(id=body.username,role='requester',payload={'display_name':body.display_name,'password_hash':hash_password(body.password),'enabled':True,'type':'individual'}))
        audit(s,body.username,'user.self_registered',{'user_id':body.username,'role':'requester'})
    return authenticate(body.username,body.password)
@app.get('/api/auth/me',tags=['Authentication'])
def me(actor=Depends(user)): return {'id':str(actor),'role':role_of(actor),'demo_mode':DEMO,'access_scope':getattr(actor,'access_scope','standard')}
@app.post('/api/auth/logout',tags=['Authentication'])
def logout(actor=Depends(user)):
    with Session.begin() as s:
        get(s,AuthSession,actor.session_id).revoked=True
        audit(s,actor,'auth.logout',{'session_revoked':True})
    return {'revoked':True}
@app.post('/api/users',tags=['Private Administration'])
def create_user(body:CreateUserBody,actor=Depends(user)):
    require_owner(actor)
    with Session.begin() as s:
        if s.get(User,body.username): raise HTTPException(409,'Username already exists')
        s.add(User(id=body.username,role=body.role,payload={'display_name':body.display_name,'password_hash':hash_password(body.password),'enabled':True,'type':'individual','access_scope':body.access_scope}))
        audit(s,actor,'user.created',{'user_id':body.username,'role':body.role})
    return {'id':body.username,'role':body.role,'display_name':body.display_name,'enabled':True}
@app.get('/api/users',tags=['Private Administration'],response_model=Page)
def list_users(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),actor=Depends(user)):
    require_owner(actor)
    with Session() as s: return database_page(s,select(User).order_by(User.id),offset,limit,lambda r:{'id':r.id,'role':r.role,'display_name':r.payload.get('display_name',r.id),'enabled':r.payload.get('enabled',True)})
@app.post('/api/users/{user_id}/disable',tags=['Private Administration'])
def disable_user(user_id:str,body:Note,actor=Depends(user)):
    require_owner(actor)
    if user_id==str(actor): raise HTTPException(409,'Cannot disable your own account')
    with Session.begin() as s:
        account=get(s,User,user_id); account.payload={**account.payload,'enabled':False}
        for session in s.scalars(select(AuthSession).where(AuthSession.user_id==user_id)): session.revoked=True
        audit(s,actor,'user.disabled',{'user_id':user_id,'reason':body.reason})
    return {'id':user_id,'enabled':False}
@app.get('/api/overview',tags=['Overview'])
def overview(actor=Depends(user)):
    with Session() as s:
        from .db import Item,Supplier
        def count(statement): return select(func.count()).select_from(statement.subquery()).scalar_subquery()
        pending=select(RequirementRecord.id).where(RequirementRecord.payload['approval_status'].as_string()=='pending')
        if role_of(actor)=='requester': pending=pending.where(RequirementRecord.run_id.in_(run_query(actor).with_only_columns(Run.id)))
        counters=s.execute(select(count(select(Item.id)).label('items'),count(select(Supplier.id)).label('suppliers'),count(select(Contract.id)).label('contracts'),count(run_query(actor).with_only_columns(Run.id)).label('runs'),count(pending).label('pending_requirements'),count(select(PurchaseOrder.id)).label('purchase_orders'),count(select(SourcingRequest.id)).label('sourcing_requests'))).one()._mapping
        latest=s.scalar(run_query(actor).order_by(Run.created_at.desc(),Run.id).limit(1))
        result=dict(counters)
        if role_of(actor)=='requester': result.update(purchase_orders=0,sourcing_requests=0)
        return {**result,'latest_run':compact_run(latest.payload) if latest else None}
@app.get('/api/master-data',tags=['Reference data'])
def masters(actor=Depends(user)):
    with Session() as s:
        d=current_data(s)
        return {'items':list(d.items.values()),'plants':list(d.plants.values()),'suppliers':list(d.suppliers.values())}

@app.post('/api/process-batch',tags=['Batch Lab'],response_model=RunResponse)
async def batch(file:UploadFile=File(...),policy_version:str|None=Form(None),actor=Depends(user)):
    consume_rate_limit(actor,'batch',60)
    rows=read_csv(await content(file,{'.csv'}),INPUT_COLUMNS)
    if role_of(actor)=='requester':
        for row in rows: row['requester']=str(actor)
    with Session.begin() as s: return execute_run(s,rows,policy_version or None,actor)

async def demo_result(file):
    from .demo import dataset,batch as example_batch
    rows=read_csv(await content(file,{'.csv'}),INPUT_COLUMNS) if file is not None else example_batch()
    if len(rows)>200: raise ValueError('Isolated demo accepts at most 200 rows; use ordinary Batch Lab for assessment batches')
    return process(rows,dataset(),[initial_policy()],'5.0')

@app.get('/api/demo/input.csv',tags=['Isolated Demo'],response_class=Response,responses={200:{'content':{'text/csv':{'schema':{'type':'string'}}}}})
def demo_input(actor=Depends(user)):
    from .demo import batch as example_batch
    return Response(csv_bytes(example_batch(),INPUT_COLUMNS),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="synthetic-demo-input.csv"'})

@app.post('/api/demo/preview',tags=['Isolated Demo'],response_model=DemoPreviewResponse)
async def demo_preview(file:UploadFile|None=File(None),actor=Depends(user)):
    return {'mode':'synthetic_preview','persistent':False,'policy_version':'5.0','source_note':'Fictional DEMO-prefixed inputs calculated with the real engine and a separate v5.0 policy. No assessment data, purchasing records or live ceilings are changed.','result':await demo_result(file)}

@app.post('/api/demo/export.csv',tags=['Isolated Demo'],response_class=Response,responses={200:{'content':{'text/csv':{'schema':{'type':'string'}}}}})
async def demo_export(file:UploadFile|None=File(None),actor=Depends(user)):
    result=await demo_result(file)
    return Response(csv_bytes(result['rows']),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="synthetic-demo-decisions.csv"'})
@app.get('/api/runs',tags=['Batch Lab'],response_model=Page)
def runs(offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),actor=Depends(user)):
    with Session() as s: return database_page(s,run_query(actor).order_by(Run.created_at.desc(),Run.id),offset,limit,lambda r:compact_run(r.payload))
@app.get('/api/runs/{run_id}',tags=['Batch Lab'],response_model=RunResponse)
def run_detail(run_id:str,actor=Depends(user)):
    with Session() as s: return accessible_run(s,run_id,actor).payload
@app.get('/api/runs/{run_id}/export.csv',tags=['Batch Lab'],response_class=Response,responses={200:{'content':{'text/csv':{'schema':{'type':'string'}}}}})
def run_export(run_id:str,actor=Depends(user)):
    with Session() as s: return Response(csv_bytes(accessible_run(s,run_id,actor).payload['rows']),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{run_id}.csv"'})
@app.post('/api/runs/{run_id}/replay',tags=['Batch Lab'])
def replay(run_id:str,actor=Depends(user)):
    with Session() as s:
        old=accessible_run(s,run_id,actor).payload; snapshot=get(s,Dataset,old['data_hash']).payload
        result=process(old['input'],Data(**snapshot),old['policy_snapshots'],old['explicit_policy'])
        return {'run_id':run_id,'matches':result['output_hash']==old['output_hash'],'output_hash':result['output_hash'],'result':result}
@app.get('/api/runs/{run_id}/compare/{other_id}',tags=['Batch Lab'],response_model=ComparisonResponse)
def compare(run_id:str,other_id:str,actor=Depends(user)):
    with Session() as s: return comparison(accessible_run(s,run_id,actor).payload,accessible_run(s,other_id,actor).payload)

@app.get('/api/requirements',tags=['Buyer Inbox'],response_model=Page)
def requirements(run_id:str|None=None,route:str|None=None,status:str|None=None,search:str=Query('',max_length=200),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),actor=Depends(user)):
    with Session() as s:
        stmt=select(RequirementRecord)
        if role_of(actor)=='requester': stmt=stmt.where(RequirementRecord.run_id.in_(run_query(actor).with_only_columns(Run.id)))
        if run_id: stmt=stmt.where(RequirementRecord.run_id==run_id)
        if route: stmt=stmt.where(RequirementRecord.payload['route'].as_string()==route)
        if status: stmt=stmt.where(RequirementRecord.payload['approval_status'].as_string()==status)
        if search: stmt=stmt.where(or_(*[func.lower(RequirementRecord.payload[key].as_string()).contains(search.lower(),autoescape=True) for key in ['description','item_code','plant']]))
        stmt=stmt.order_by(RequirementRecord.payload['created_at'].as_string(),RequirementRecord.id)
        return database_page(s,stmt,offset,limit,lambda r:dict(r.payload,record_id=r.id,run_id=r.run_id))
@app.get('/api/requirements/{requirement_id}',tags=['Decision Trace'],response_model=RequirementResponse)
def requirement_detail(requirement_id:str,run_id:str,actor=Depends(user)):
    with Session() as s:
        accessible_run(s,run_id,actor)
        r=get(s,RequirementRecord,run_id+':'+requirement_id)
        return dict(r.payload,record_id=r.id,run_id=run_id)

@app.get('/api/policy-schema',tags=['Policy Studio'])
def policy_schema(actor=Depends(user)):
    return {'facts':{k:v.__name__ for k,v in FACTS.items()},'operators':sorted(OPS),'boolean_operators':['all','any','not'],'routes':sorted(ROUTES),'example':initial_policy()}
@app.get('/api/policies',tags=['Policy Studio'])
def list_policies(actor=Depends(user)):
    with Session() as s: return {'items':[{**r.payload,'status':r.status,'id':r.id} for r in s.scalars(select(Policy))]}
def policy_content_hash(policy):
    definition=PolicyDefinition.model_validate(policy).model_dump(by_alias=True)
    return digest({'parameters':definition['parameters'],'rules':definition['rules']})

def new_policy(s,body,actor,interpretation=None):
    policy=validate_policy(body.policy.model_dump(by_alias=True))
    if s.get(Policy,policy['version']): raise HTTPException(409,'Policy version already exists')
    base=get(s,Policy,body.base_version)
    content_hash=policy_content_hash(policy)
    payload={**policy,'governance':{'base_version':body.base_version,'source_text':body.source_text,'original_source_text':body.source_text,'source_hash':hashlib.sha256(body.source_text.encode()).hexdigest(),'interpretation_definition_hash':content_hash,'manual_reconciled':False,'proposed_by':actor,'proposed_at':db.now(),'reviewed':False,'diff':field_diff(base.payload,policy)}}
    if interpretation: payload['governance']['interpretation']={k:v for k,v in interpretation.items() if k!='policy'}
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
        interpreted=interpret(base,body.text,body.version,body.effective_date.isoformat(),current_data(s))
        result=new_policy(s,PolicyBody(policy=interpreted['policy'],source_text=body.text,base_version=body.base_version),actor,interpreted)
        return {**result,'interpretation':{k:v for k,v in interpreted.items() if k!='policy'}|{'requires_manual_review':True,'warning':'Review every proposed condition and priority. Unresolved clauses require manual authoring and explicit verification.'}}
@app.put('/api/policies/{policy_id}',tags=['Policy Studio'],response_model=PolicyResponse)
def edit_policy(policy_id:str,body:PolicyBody,actor=Depends(user)):
    require(actor,'admin')
    with Session.begin() as s:
        r=get(s,Policy,policy_id,lock=True)
        if r.status!='draft': raise HTTPException(409,'Approved policy snapshots are immutable')
        p=validate_policy(body.policy.model_dump(by_alias=True))
        if p['version']!=policy_id: raise ValueError('Cannot rename policy version')
        base=get(s,Policy,body.base_version)
        governance=r.payload.get('governance',{})
        original_hash=governance.get('interpretation_definition_hash',policy_content_hash(r.payload))
        reconciled=policy_content_hash(p)!=original_hash
        r.payload={**p,'governance':{**governance,'interpretation_definition_hash':original_hash,'manual_reconciled':reconciled,'source_text':body.source_text,'base_version':body.base_version,'reviewed':False,'diff':field_diff(base.payload,p)}}
        audit(s,actor,'policy.edited',{'version':policy_id})
        return {**r.payload,'status':r.status,'id':r.id}
@app.post('/api/policies/upload-amendment',tags=['Policy Studio'],response_model=PolicyResponse)
async def upload_amendment(file:UploadFile=File(...),version:str=Form(...),effective_date:str=Form(...),base_version:str=Form('5.0'),actor=Depends(user)):
    consume_rate_limit(actor,'policy-upload',20)
    require(actor,'admin'); raw=await content(file,{'.pdf','.txt','.json'})
    text_source=pdf_text(raw) if file.filename.lower().endswith('.pdf') else raw.decode('utf-8-sig')
    with Session.begin() as s:
        base=deepcopy(get(s,Policy,base_version).payload); base.pop('governance',None)
        if file.filename.lower().endswith('.json'):
            p=json.loads(text_source); p['version']=version; p['effective_date']=effective_date
            interpreted={'policy':p,'detected_changes':['Structured policy document loaded'],'unresolved_clauses':[],'complete':True}
        else: interpreted=interpret(base,text_source,version,effective_date,current_data(s)); p=interpreted['policy']
        result=new_policy(s,PolicyBody(policy=p,source_text=text_source,base_version=base_version),actor,interpreted)
        record=s.get(Policy,version)
        record.payload={**record.payload,'governance':{**record.payload['governance'],'source_bytes_hash':hashlib.sha256(raw).hexdigest(),'source_bytes_hash_type':'sha256-upload-bytes'}}
        result={**result,'governance':record.payload['governance']}
        return {**result,'interpretation':{k:v for k,v in interpreted.items() if k!='policy'}|{'requires_manual_review':True,'warning':'Review scope, operators and priority. Unresolved clauses require explicit manual verification; PDF signatures are not cryptographically verified.'}}
@app.post('/api/policies/{policy_id}/review',tags=['Policy Studio'],response_model=PolicyResponse)
def review_policy(policy_id:str,body:PolicyReviewBody,actor=Depends(user)):
    require(actor,'admin')
    with Session.begin() as s:
        p=get(s,Policy,policy_id,lock=True)
        if p.status!='draft': raise HTTPException(409,'Only drafts can be reviewed')
        if p.payload.get('governance',{}).get('interpretation',{}).get('unresolved_clauses') and (not body.manual_verification or not p.payload.get('governance',{}).get('manual_reconciled')):
            raise HTTPException(409,'Unresolved source clauses require saved structured corrections and explicit manual verification; a checkbox alone cannot implement them')
        p.payload={**p.payload,'governance':{**p.payload.get('governance',{}),'reviewed':True,'review_note':body.reason,'reviewed_by':actor,'reviewed_at':db.now(),'manual_verification':body.manual_verification}}
        audit(s,actor,'policy.reviewed',{'version':policy_id,'reason':body.reason})
        return {**p.payload,'id':p.id,'status':p.status}
@app.post('/api/policies/{policy_id}/approve',tags=['Policy Studio'],response_model=PolicyResponse)
def approve_policy(policy_id:str,body:Note,actor=Depends(user)):
    require(actor,'admin')
    with Session.begin() as s:
        p=get(s,Policy,policy_id,lock=True)
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
        db.transaction_lock(s,db.POLICY_CALENDAR_LOCK,exclusive=True)
        p=get(s,Policy,policy_id,lock=True)
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
        db.transaction_lock(s,db.POLICY_CALENDAR_LOCK,exclusive=True)
        p=get(s,Policy,policy_id,lock=True)
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
            committed=number(c['consumed_value'])-number(c['baseline_consumed_value'])
            rows.append({**c,'committed_value':str(committed),'remaining_value':str(number(c['value_cap'])-number(c['consumed_value'])),'supplier_status':d.suppliers[c['supplier_id']]['status'],'valid_as_of':c['start_date']<=day<=c['end_date']})
        return {**page(rows,offset,limit),'as_of':day}
@app.post('/api/contracts/upload',tags=['Contract Vault'])
async def upload_contract(file:UploadFile=File(...),actor=Depends(user)):
    consume_rate_limit(actor,'contract-upload',20)
    require(actor,'admin','buyer'); raw=await content(file,{'.pdf'}); source=pdf_text(raw,allow_empty=True)
    try: proposed=extract_contract(raw); error=None
    except ValueError as exc: proposed=None; error=str(exc)
    proposal_id='CP-'+uuid4().hex
    with Session.begin() as s:
        if proposed:
            try: validate_contract(proposed,current_data(s))
            except ValueError as exc: error=str(exc)
        source_hash=hashlib.sha256(raw).hexdigest()
        payload={'id':proposal_id,'status':'pending_review','contract':proposed,'source_text':source,'source_hash':source_hash,'source_hash_type':'sha256-pdf-bytes','manual_entry_required':proposed is None or bool(error),'validation_error':error,'signature_verified':False,'actor':actor}
        s.add(ContractProposal(id=proposal_id,payload=payload)); audit(s,actor,'contract.uploaded',{'proposal_id':proposal_id,'source_hash':source_hash})
        return payload
@app.get('/api/contracts/proposals',tags=['Contract Vault'])
def contract_proposals(actor=Depends(user)):
    require(actor,'admin','buyer')
    with Session() as s: return {'items':[r.payload for r in s.scalars(select(ContractProposal))]}
@app.get('/api/contracts/{contract_id}',tags=['Contract Vault'])
def contract_detail(contract_id:str,as_of:date|None=None,actor=Depends(user)):
    with Session() as s:
        d=current_data(s)
        c=next((c for c in d.contracts if c['contract_id']==contract_id),None)
        if c is None: raise HTTPException(404,'Contract not found')
        day=(as_of or business_today()).isoformat()
        committed=number(c['consumed_value'])-number(c['baseline_consumed_value'])
        return {**c,'committed_value':str(committed),'remaining_value':str(number(c['value_cap'])-number(c['consumed_value'])),'supplier_status':d.suppliers[c['supplier_id']]['status'],'valid_as_of':c['start_date']<=day<=c['end_date']}
@app.post('/api/contracts/proposals/{proposal_id}/approve',tags=['Contract Vault'])
def approve_contract(proposal_id:str,body:ContractBody,actor=Depends(user)):
    require(actor,'admin','buyer')
    with mutation_lock,Session.begin() as s:
        db.transaction_lock(s,db.CATALOG_LOCK,exclusive=True)
        proposal=get(s,ContractProposal,proposal_id,lock=True)
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
    db.transaction_lock(s,db.CATALOG_LOCK)
    locked_contracts={c.id:c for c in s.scalars(select(Contract).order_by(Contract.id).with_for_update())}
    db.transaction_lock(s,db.POLICY_CALENDAR_LOCK)
    policy_snapshot=policies(s,lock=True)
    r=get(s,RequirementRecord,run_id+':'+requirement_id,lock=True)
    if r.payload['approval_status']!='pending': raise HTTPException(409,'Requirement already actioned')
    target=r.payload
    if target['route']=='NOT_PROCESSED': raise HTTPException(409,'Invalid requirement cannot be approved')
    ensure_current_policy(s,target,policy_snapshot)
    required=target.get('required_approvals',1)
    if required>1:
        votes=list(target.get('approval_votes',[]))
        if any(v['actor']==str(actor) for v in votes): raise HTTPException(409,'A distinct second reviewer is required; you already recorded an approval')
        votes.append({'actor':str(actor),'reason':reason,'at':db.now()})
        r.payload={**target,'approval_votes':votes};target=r.payload
        audit(s,actor,'sourcing.approval_recorded',{'run_id':run_id,'requirement_id':requirement_id,'approval_count':len(votes),'required_approvals':required,'reason':reason})
        if len(votes)<required:
            return {'id':'REVIEW-'+digest([run_id,requirement_id])[:16],'run_id':run_id,'requirements':[requirement_id],'recommendations':[target],'actor':str(actor),'approved_at':'','reason':reason,'status':'awaiting_approval','approval_count':len(votes),'required_approvals':required}
    records=[r]
    if target['po_id']:
        records=[x for x in s.scalars(select(RequirementRecord).where(RequirementRecord.run_id==run_id)) if x.payload['po_id']==target['po_id'] and x.payload['approval_status']=='pending']
    action_id=target['po_id'] or 'SRC-'+digest([run_id,requirement_id])[:16]
    d=current_data(s)
    remaining={c['contract_id']:number(c['value_cap'])-number(c['consumed_value']) for c in d.contracts}
    source_keys=[digest([line['pr_no'],line['pr_line']]) for record in records for line in record.payload['lines']]
    if len(source_keys)!=len(set(source_keys)) or s.scalar(select(Commitment.id).where(Commitment.id.in_(source_keys)).limit(1)):
        raise HTTPException(409,'A PR line has already been approved in another run')
    for record in records:
        rec=record.payload
        ensure_current_policy(s,rec,policy_snapshot)
        for line in rec['lines']:
            key=digest([line['pr_no'],line['pr_line']])
            s.add(Commitment(id=key,action_id=action_id))
        if rec['supplier_id'] and d.suppliers.get(rec['supplier_id'],{}).get('status')!='Active': raise HTTPException(409,'Supplier is no longer Active')
        cid=rec['evidence'].get('selected_contract')
        if cid:
            c=locked_contracts[cid].payload
            if c['supplier_id']!=rec['supplier_id'] or not c['start_date']<=rec['created_at'][:10]<=c['end_date']:
                raise HTTPException(409,'Contract supplier or validity changed; reprocess batch')
            actual=next((l for l in c['lines'] if l['item_code']==rec['item_code']),None)
            if not actual or number(actual['rate'])!=number(rec['unit_price']): raise HTTPException(409,'Contract rate changed; reprocess batch')
            amount=number(rec['quantity'])*number(actual['rate'])
            if amount>remaining[cid]: raise HTTPException(409,'Contract headroom changed; reprocess batch')
            remaining[cid]-=amount
            s.add(ContractLedger(id=run_id+':'+record.group_id,contract_id=cid,payload={'amount':str(amount),'action_id':action_id,'actor':actor,'timestamp':db.now()})); s.flush()
        record.payload={**rec,'approval_status':'approved','approved_by':actor,'approved_at':db.now(),'action_id':action_id}
    payload={'id':action_id,'run_id':run_id,'requirements':[x.group_id for x in records],'recommendations':[x.payload for x in records],'actor':actor,'approved_at':db.now(),'reason':reason,'status':'approved'}
    if target['decision']=='PO':
        s.add(PurchaseOrder(id=action_id,run_id=run_id,supplier_id=target['supplier_id'],payload=payload)); s.flush()
        for record in records: s.add(PurchaseOrderLine(id=action_id+':'+record.group_id,order_id=action_id,requirement_id=record.id,payload=record.payload))
    else: s.add(SourcingRequest(id=action_id,run_id=run_id,payload=payload))
    audit(s,actor,'purchase_order.approved' if target['decision']=='PO' else 'sourcing.approved',{'id':action_id,'run_id':run_id,'requirements':payload['requirements'],'reason':reason})
    return payload

def ensure_current_policy(s,requirement,policy_snapshot=None):
    try: current=select_policy(policy_snapshot if policy_snapshot is not None else policies(s,lock=True),date.fromisoformat(requirement['created_at'][:10]))
    except ValueError: raise HTTPException(409,'No active effective policy is available; reprocess after policy review')
    if current['version']!=requirement['policy_version']:
        raise HTTPException(409,'A newer effective policy applies; reprocess before recording a purchasing action')

@app.post('/api/requirements/{requirement_id}/approve',tags=['Buyer Inbox'],response_model=ActionResponse)
def approve_requirement(requirement_id:str,body:Note,run_id:str,actor=Depends(user)):
    require(actor,'buyer','admin')
    with mutation_lock,Session.begin() as s: return commit_requirement(s,run_id,requirement_id,actor,body.reason)
@app.post('/api/requirements/{requirement_id}/override',tags=['Buyer Inbox'],response_model=ActionResponse)
def override_requirement(requirement_id:str,body:OverrideBody,run_id:str,actor=Depends(user)):
    require(actor,'buyer','admin')
    with mutation_lock,Session.begin() as s:
        db.transaction_lock(s,db.CATALOG_LOCK)
        db.transaction_lock(s,db.POLICY_CALENDAR_LOCK)
        r=get(s,RequirementRecord,run_id+':'+requirement_id,lock=True)
        if r.payload['approval_status']!='pending': raise HTTPException(409,'Requirement already actioned')
        ensure_current_policy(s,r.payload)
        if r.payload.get('required_approvals',1)>1: raise HTTPException(409,'This requirement needs distinct sourcing approvals; an override cannot bypass that control')
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
    require(actor,'buyer','admin')
    with Session() as s: return database_page(s,select(PurchaseOrder).order_by(PurchaseOrder.id),offset,limit)
@app.get('/api/purchase-orders/{order_id}',tags=['Purchase Orders'])
def purchase_order(order_id:str,actor=Depends(user)):
    require(actor,'buyer','admin')
    with Session() as s: return get(s,PurchaseOrder,order_id).payload
@app.get('/api/sourcing',tags=['Sourcing'],response_model=Page)
def sourcing(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),actor=Depends(user)):
    require(actor,'buyer','admin')
    with Session() as s: return database_page(s,select(SourcingRequest).order_by(SourcingRequest.id),offset,limit)
@app.get('/api/sourcing/{sourcing_id}',tags=['Sourcing'])
def sourcing_detail(sourcing_id:str,actor=Depends(user)):
    require(actor,'buyer','admin')
    with Session() as s: return get(s,SourcingRequest,sourcing_id).payload
@app.get('/api/audit',tags=['Audit Trail'],response_model=Page)
def audit_events(action:str|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),actor=Depends(user)):
    require(actor,'buyer','admin')
    with Session() as s:
        statement=select(Audit).order_by(Audit.created_at.desc(),Audit.id)
        if action: statement=statement.where(Audit.payload['action'].as_string()==action)
        return database_page(s,statement,offset,limit,lambda r:{'id':r.id,'created_at':r.created_at,**r.payload})

@app.post('/api/chat/messages',tags=['Request Desk'],response_model=ChatResponse)
def chat_message(body:ChatBody,actor=Depends(user)):
    from zoneinfo import ZoneInfo
    consume_rate_limit(actor,'chat',120)
    with mutation_lock,Session.begin() as s:
        session_id=body.session_id or 'CHAT-'+uuid4().hex
        record=s.scalar(select(Chat).where(Chat.id==session_id).with_for_update())
        if body.session_id and not record: raise HTTPException(404,'Chat session not found')
        payload=deepcopy(record.payload) if record else {'actor':actor,'messages':[],'state':{}}
        if payload['actor']!=actor: raise HTTPException(403,'This session belongs to another actor')
        if len(payload['messages'])>=400: raise HTTPException(409,'Chat session limit reached; start a new session')
        payload['messages'].append({'role':'user','content':body.message,'timestamp':db.now()})
        result=None
        if body.message.strip().lower() in {'confirm','yes','submit'} and payload['state'].get('ready'):
            state=payload['state']; item=current_data(s).items.get(state['item_code'],{})
            created=datetime.now(ZoneInfo('Asia/Kolkata')).replace(tzinfo=None).isoformat(timespec='seconds')
            submission=int(payload.get('submission_count',0))+1
            row={'pr_no':f'PR-CHAT-{session_id[-12:].upper()}-{submission:04d}','pr_line':'1','created_at':created,'requester':actor,'department':'Chat intake','plant':state['plant'],'item_code':'' if state['item_code']=='NEW' else state['item_code'],'description':item.get('description',state['description']),'quantity':state['quantity'],'uom':state['uom'],'estimated_unit_price':state.get('estimated_unit_price',''),'need_by_date':state['need_by_date'],'urgency':state['urgency']}
            result=execute_run(s,[row],None,actor)
            if result['issues']: reply='Request validation failed: '+str(result['issues'])
            else: reply='PR created. '+result['rows'][0]['reason']; payload['state']={}; payload['submission_count']=submission
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
    return FileResponse(built if built.is_file() else root/'frontend'/'index.html',headers={'Cache-Control':'no-store'})

@app.post('/api/admin/import-data',tags=['Private Administration'])
async def import_data(file:UploadFile=File(...),actor=Depends(user)):
    from io import BytesIO
    from pathlib import PurePosixPath
    import tempfile,zipfile
    from .ingest import load_kit
    require_owner(actor); raw=await content(file,{'.zip'})
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
                db.transaction_lock(s,db.CATALOG_LOCK,exclusive=True)
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
            statuses=[422,409,413,429,503] if method in {'post','put'} else [422,503]
            if path.startswith('/api/') and path not in {'/api/auth/login','/api/auth/register','/api/auth/options'}: statuses += [401,403,404]
            if path=='/api/auth/login': statuses += [401,429]
            if path=='/api/auth/register': statuses += [403,429]
            for status in statuses:
                operation.setdefault('responses',{})[str(status)]={'description':{401:'Sign-in required or invalid credentials',403:'Role not permitted',404:'Record not found',409:'Conflicting action or record',413:'Upload too large',422:'Validation failed',429:'Request temporarily throttled; see Retry-After',503:'Storage temporarily unavailable; retry later'}[status],'content':{'application/json':{'schema':{'$ref':'#/components/schemas/ErrorResponse'}}}}
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
    # Never serve SPA HTML for a missing chunk, stylesheet or image. Browsers
    # otherwise report MIME errors and a cached release can render blank.
    if frontend_path.startswith('assets/') or Path(frontend_path).suffix.lower() in {'.js','.css','.map','.png','.jpg','.jpeg','.webp','.svg','.woff','.woff2','.mp4','.ico','.json'}:
        raise HTTPException(404,'Frontend asset not found; reload the current application')
    if (root/'index.html').is_file(): return FileResponse(root/'index.html',headers={'Cache-Control':'no-store'})
    raise HTTPException(404,'Arena frontend has not been integrated')

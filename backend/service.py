from uuid import uuid4
from copy import deepcopy
from sqlalchemy import select,delete
from .db import Plant,Item,Supplier,History,Contract,ContractLine,Dataset,Policy,Run,RequirementRecord,Audit,ContractLedger,now
from .domain import Data,digest,number
from .engine import process
from .policy import initial_policy,validate_policy
from .db import Requisition,RequisitionLine,Membership,transaction_lock,CATALOG_LOCK

def audit(session,actor,action,details):
    session.add(Audit(id=str(uuid4()),created_at=now(),payload={'actor':actor,'action':action,'details':details}))

def current_data(session):
    transaction_lock(session,CATALOG_LOCK)
    def keyed(model): return {r.id:r.payload for r in session.scalars(select(model)).all()}
    contracts=[deepcopy(r.payload) for r in session.scalars(select(Contract))]
    ledger={}
    for row in session.scalars(select(ContractLedger)):
        ledger[row.contract_id]=ledger.get(row.contract_id,number(0))+number(row.payload['amount'])
    for c in contracts:
        c['baseline_consumed_value']=c['consumed_value']
        c['consumed_value']=str(number(c['consumed_value'])+ledger.get(c['contract_id'],number(0)))
    return Data(keyed(Item),keyed(Supplier),keyed(Plant),[r.payload for r in session.scalars(select(History))],contracts)

def save_data(session,data):
    transaction_lock(session,CATALOG_LOCK,exclusive=True)
    for model,rows in [(Plant,data.plants),(Item,data.items),(Supplier,data.suppliers)]:
        existing={row.id:row for row in session.scalars(select(model))}
        for key,payload in rows.items():
            if key in existing: existing[key].payload=payload
            else: session.add(model(id=key,payload=payload))
    session.flush()
    history_ids=set(session.scalars(select(History.id)))
    for h in data.history:
        key=digest(h)
        if key not in history_ids:
            session.add(History(id=key,item_id=h['item_code'],supplier_id=h['supplier_id'],payload=h)); history_ids.add(key)
    contracts={row.id:row for row in session.scalars(select(Contract))}
    for c in data.contracts:
        if c['contract_id'] in contracts:
            contracts[c['contract_id']].supplier_id=c['supplier_id']; contracts[c['contract_id']].payload=c
        else: session.add(Contract(id=c['contract_id'],supplier_id=c['supplier_id'],payload=c))
    session.flush()
    session.execute(delete(ContractLine).where(ContractLine.contract_id.in_([c['contract_id'] for c in data.contracts])))
    for c in data.contracts:
        for l in c['lines']: session.add(ContractLine(id=c['contract_id']+':'+l['item_code'],contract_id=c['contract_id'],item_id=l['item_code'],payload=l))
    session.flush()
    snapshot=data.snapshot(); key=digest(snapshot)
    if not session.get(Dataset,key): session.add(Dataset(id=key,payload=snapshot))
    if not session.get(Policy,'5.0'): session.add(Policy(id='5.0',status='active',payload=initial_policy()))
    return key

def policies(session,lock=False):
    statement=select(Policy).order_by(Policy.id)
    if lock: statement=statement.with_for_update(read=True)
    return [{**r.payload,'status':r.status} for r in session.scalars(statement)]

def execute_run(session,rows,explicit,actor,data=None,policy_list=None,policy_mode='pinned'):
    data=data or current_data(session); ps=policy_list or [p for p in policies(session) if p['status']=='active' or (explicit and p['status']=='superseded')]
    calendar_version=None
    if policy_mode not in {'pinned','calendar'}: raise ValueError('Unknown policy application mode')
    if policy_mode=='calendar' and explicit:
        target=next((p for p in ps if p['version']==explicit and p.get('status','active')=='active'),None)
        if not target: raise ValueError('Activate the selected amendment before calendar processing')
        calendar_version=explicit
        ps=[p for p in ps if p.get('status','active')=='active' and (p['effective_date']<target['effective_date'] or p['version']==explicit)]
        explicit=None
    elif explicit: ps=[p for p in ps if p['version']==explicit]
    ps=sorted(ps,key=lambda p:(p['effective_date'],p['version']))
    if not data.items: raise ValueError('Import private master data before processing')
    result=process(rows,data,ps,explicit)
    used_versions={row['policy_version'] for row in result['rows']}
    snapshot_policies=[p for p in ps if p['version'] in used_versions]
    data_hash=digest(data.snapshot()); input_hash=digest(sorted(rows,key=lambda r:(r['pr_no'],r['pr_line'],digest(r))))
    # Governance status can change after activation/withdrawal without changing
    # an approved policy's immutable content. Unused versions are not inputs.
    policy_hash=digest([{k:v for k,v in p.items() if k not in {'id','status','governance'}} for p in snapshot_policies])
    selection={'mode':'calendar','through_version':calendar_version} if calendar_version else explicit
    run_id='RUN-'+digest([input_hash,data_hash,policy_hash,selection,str(actor)])[:20]
    existing=session.get(Run,run_id)
    if existing: return existing.payload
    if not session.get(Dataset,data_hash): session.add(Dataset(id=data_hash,payload=data.snapshot())); session.flush()
    payload={**result,'id':run_id,'created_at':now(),'input_hash':input_hash,'data_hash':data_hash,'policy_hash':policy_hash,'policy_snapshots':deepcopy(snapshot_policies),'explicit_policy':explicit,'policy_mode':'pinned' if explicit else 'calendar','calendar_version':calendar_version,'input':rows,'status':'completed','actor':actor}
    session.add(Run(id=run_id,created_at=payload['created_at'],input_hash=input_hash,data_hash=data_hash,payload=payload)); session.flush()
    pr_ids=set(session.scalars(select(Requisition.id).where(Requisition.id.in_([row['pr_no'] for row in rows]))))
    for pr in sorted({row['pr_no'] for row in rows}-pr_ids): session.add(Requisition(id=pr,payload={'pr_no':pr}))
    session.flush()
    line_ids=set(session.scalars(select(RequisitionLine.id).where(RequisitionLine.id.in_([digest(row) for row in rows]))))
    for row in rows:
        key=digest(row)
        if key not in line_ids:
            session.add(RequisitionLine(id=key,requisition_id=row['pr_no'],payload=row)); line_ids.add(key)
    session.flush()
    for req in result['requirements']:
        key=run_id+':'+req['id']
        session.add(RequirementRecord(id=key,run_id=run_id,group_id=req['id'],payload=req))
    session.flush()
    for req in result['requirements']:
        key=run_id+':'+req['id']
        for row in req['lines']: session.add(Membership(id=key+':'+digest(row),requirement_id=key,pr_line_id=digest(row)))
    audit(session,actor,'batch.processed',{'run_id':run_id,'output_hash':result['output_hash'],'count':len(rows)})
    return payload

def comparison(before,after):
    old={(r['pr_no'],r['pr_line']):r for r in before['rows']}
    fields=['route','supplier_id','group_value_inr','group_id','po_id','reason','suggested_supplier_ids']
    changes=[]
    for r in after['rows']:
        a=old.get((r['pr_no'],r['pr_line']),{})
        diff={k:{'before':a.get(k),'after':r[k]} for k in fields if a.get(k)!=r[k]}
        business={k:v for k,v in diff.items() if k!='reason'}
        if diff: changes.append({'pr_no':r['pr_no'],'pr_line':r['pr_line'],'business_changed':bool(business),'changes':diff})
    return {'affected_lines':sum(c['business_changed'] for c in changes),'explanation_changes':len(changes),'changes':changes}

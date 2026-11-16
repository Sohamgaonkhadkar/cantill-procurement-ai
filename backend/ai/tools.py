"""Finite, read-only tool registry. No URL, SQL, code or purchasing writes."""
from datetime import date,datetime
from zoneinfo import ZoneInfo
import json
from pydantic import Field
from sqlalchemy import select
from fastapi import HTTPException
from ..db import Policy,Run,RequirementRecord
from ..service import current_data,policies
from ..engine import select_policy
from ..matching import resolve
from ..suppliers import preferred
from ..domain import number,digest
from ..amendments import policy_diff
from .schemas import Strict
from .safety import authorize_actor
from .retrieval import search
from .config import settings

class Empty(Strict):pass
class AsOf(Strict):as_of_date:date|None=None
class PolicyQuery(AsOf):policy_version:str|None=Field(None,max_length=128)
class SearchQuery(PolicyQuery):query:str=Field(min_length=1,max_length=500)
class CatalogQuery(Strict):description:str=Field(min_length=1,max_length=500)
class ItemQuery(AsOf):item_code:str=Field(min_length=1,max_length=128)
class SupplierQuery(Strict):supplier_id:str=Field(min_length=1,max_length=128)
class ContractQuery(AsOf):contract_id:str=Field(min_length=1,max_length=128)
class RequirementQuery(Strict):
    run_id:str=Field(min_length=1,max_length=128)
    requirement_id:str=Field(min_length=1,max_length=128)
class CompareQuery(Strict):
    version_a:str=Field(min_length=1,max_length=128)
    version_b:str=Field(min_length=1,max_length=128)

REGISTRY={
 'get_active_policy':(PolicyQuery,'Read the effective enforced policy for the stated date.'),
 'search_policy_clauses':(SearchQuery,'Retrieve authorized clauses with source citations; defaults to current policy.'),
 'search_contracts':(SearchQuery,'Search authorized contract terms and current validity; no ceiling is cached.'),
 'get_contract_details':(ContractQuery,'Read exact current contract terms, consumed value and available ceiling.'),
 'get_supplier_details':(SupplierQuery,'Read the actual supplier master status and performance.'),
 'get_preferred_suppliers':(ItemQuery,'Return authoritative supplier ranking and price references for an item/date.'),
 'get_master_item':(ItemQuery,'Read an exact catalog item and unit.'),
 'search_catalog_items':(CatalogQuery,'Use the existing item matcher; incomplete specifications remain unresolved.'),
 'get_purchase_request':(RequirementQuery,'Read a permitted requirement identified by both run and requirement ID.'),
 'get_decision_evidence':(RequirementQuery,'Read the actual grouping, valuation, contract rejection, rule and supplier evidence.'),
 'get_recent_user_requests':(Empty,'Read the current user\'s five latest runs.'),
 'compare_policy_versions':(CompareQuery,'Read exact rule/parameter changes; draft versions are labeled as drafts.'),
}

def today():return datetime.now(ZoneInfo('Asia/Kolkata')).date()

def definitions(allowed=None):
    from .provider import _strict_schema
    return [{'type':'function','function':{'name':name,'description':description,'strict':True,'parameters':_strict_schema(schema.model_json_schema())}} for name,(schema,description) in REGISTRY.items() if allowed is None or name in allowed]

def _policy(session,args):return select_policy(policies(session),args.as_of_date or today(),getattr(args,'policy_version',None))

def _requirement(session,actor,args):
    # Reuse the API's existing authorization boundary; do not expand requester
    # access just because a model supplied a valid-looking identifier.
    from ..api import accessible_run,get
    accessible_run(session,args.run_id,actor)
    return get(session,RequirementRecord,args.run_id+':'+args.requirement_id).payload

def _search(session,actor,name,args,query_embedding=None,embedding_model=None):
    kind='policy' if name=='search_policy_clauses' else 'contract'
    day=args.as_of_date or today()
    matches=search(session,actor,args.query,day,policy_version=args.policy_version,source_type=kind,query_embedding=query_embedding,embedding_model=embedding_model,top_k=settings().top_k)
    if kind=='policy':
        # A clause may refer to a policy parameter (for example a history
        # lookback). Retrieve that same version's complete parameter section
        # alongside the rule so a model never needs to infer its value.
        parameters=search(session,actor,'Policy parameters',day,policy_version=args.policy_version,source_type='policy',top_k=1)
        ids={entry['citation']['id'] for entry in matches}
        matches += [entry for entry in parameters if entry['citation']['id'] not in ids]
    return {'matches':matches,'as_of_date':day.isoformat()}

def _execute(session,actor,name,args):
    day=getattr(args,'as_of_date',None) or today()
    if name=='get_active_policy':
        policy=_policy(session,args)
        return {'policy':{k:policy[k] for k in ['version','effective_date','parameters','rules']},'as_of_date':day.isoformat(),'enforced':True}
    if name in {'search_policy_clauses','search_contracts'}:
        return _search(session,actor,name,args)
    if name=='compare_policy_versions':
        a=session.get(Policy,args.version_a);b=session.get(Policy,args.version_b)
        if not a or not b:raise HTTPException(404,'Policy version not found')
        return {'version_a':a.id,'version_b':b.id,'status_a':a.status,'status_b':b.status,'effective_date_a':a.payload['effective_date'],'effective_date_b':b.payload['effective_date'],'changes':policy_diff(a.payload,b.payload),'drafts_are_not_enforced':True}
    if name in {'get_purchase_request','get_decision_evidence'}:
        record=_requirement(session,actor,args)
        return {'run_id':args.run_id,'requirement_id':args.requirement_id,'requirement':record}
    if name=='get_recent_user_requests':
        from ..api import compact_run
        records=session.scalars(select(Run).where(Run.payload['actor'].as_string()==str(actor)).order_by(Run.created_at.desc()).limit(5))
        return {'runs':[compact_run(row.payload) for row in records]}
    data=current_data(session)
    if name=='get_supplier_details':
        supplier=data.suppliers.get(args.supplier_id)
        if not supplier:raise HTTPException(404,'Supplier not found')
        return {'supplier':supplier}
    if name=='search_catalog_items':
        code,evidence=resolve('',args.description,'',data.items)
        return {'resolved_item_code':code,'matching':evidence,'items':[data.items[c['item_code']] for c in evidence.get('candidates',[])]}
    if name=='get_master_item':
        item=data.items.get(args.item_code)
        if not item:raise HTTPException(404,'Catalog item not found')
        return {'item':item}
    if name=='get_preferred_suppliers':
        if args.item_code not in data.items:raise HTTPException(404,'Catalog item not found')
        policy=_policy(session,args)
        return {'item_code':args.item_code,'as_of_date':day.isoformat(),'policy_version':policy['version'],'suppliers':preferred(data,args.item_code,day,policy)}
    if name=='get_contract_details':
        contract=next((c for c in data.contracts if c['contract_id']==args.contract_id),None)
        if not contract:raise HTTPException(404,'Contract not found')
        return {'contract':{**contract,'remaining_value':str(number(contract['value_cap'])-number(contract['consumed_value'])),'supplier_status':data.suppliers[contract['supplier_id']]['status'],'valid_as_of':contract['start_date']<=day.isoformat()<=contract['end_date']},'as_of_date':day.isoformat()}
    raise ValueError('Unknown read-only tool')

def execute(factory,actor,name,arguments,*,query_embedding=None,embedding_model=None):
    if name not in REGISTRY:raise ValueError('Tool is not in the read-only registry')
    raw=json.loads(arguments) if isinstance(arguments,str) else arguments
    args=REGISTRY[name][0].model_validate(raw)
    with factory.begin() as session:
        authorize_actor(session,actor)
        if query_embedding and name in {'search_policy_clauses','search_contracts'}:
            result=_search(session,actor,name,args,query_embedding,embedding_model)
        else:result=_execute(session,actor,name,args)
    return {'tool':name,'result':result,'source_hash':digest(result)}

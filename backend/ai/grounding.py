"""Backend-generated citations and guarded synthesis of read-only tool results."""
from copy import deepcopy
from decimal import Decimal,InvalidOperation
import json,re
from ..domain import digest
from ..workspace import isolated_demo
from .schemas import Citation
from .safety import ExternalContext
from .presentation import policy_text,passage_text

def display_answer(text):
    # Source cards retain validated IDs; conversational prose uses their titles.
    return re.sub(r'\s*\[(?:KCH|TOOL)-[A-Za-z0-9-]+(?:\s*,\s*(?:KCH|TOOL)-[A-Za-z0-9-]+)*\]','',text)

def _numbers(text):
    values=set()
    text=re.sub(r'^\s*\d+[.)]\s+','',text,flags=re.M)
    text=re.sub(r'\[(?:TOOL|KCH)-[A-Za-z0-9-]+\]','',text)
    for token in re.findall(r'(?<![\w])\d[\d,]*(?:\.\d+)?',text):
        try:values.add(str(Decimal(token.replace(',','')).normalize()))
        except InvalidOperation:pass
    return values

def validate_answer(answer,citations,evidence):
    allowed={source['id'] for source in citations}
    if any(source not in allowed for source in answer.citation_ids):return False
    if not answer.insufficient_evidence and (not answer.citation_ids or not evidence):return False
    if _numbers(answer.answer)-_numbers(json.dumps(evidence,default=str)):return False
    # Entity references must appear in the actual supplied evidence.
    entities=re.findall(r'\b(?:DEMO-[A-Z0-9-]+|ITM-\d+|RC-\d{4}-\d+|REQ-[A-Za-z0-9]+|S\d{3,})\b',answer.answer)
    source_text=json.dumps(evidence,default=str)
    return all(entity in source_text for entity in entities)

def provenance(tool_outputs):
    """Only known fictional seed facts receive automatic external approval."""
    if not isolated_demo():return False
    from ..demo import dataset
    from ..policy import initial_policy
    data=dataset();baseline=initial_policy()
    for output in tool_outputs:
        name=output['tool'];result=output['result']
        if name in {'search_policy_clauses','search_contracts'}:
            if any(not entry['external_approved'] or entry['classification'] not in {'fictional_demo','public_approved'} for entry in result.get('matches',[])):return False
        elif name=='get_active_policy':
            policy=result['policy']
            if any(policy.get(key)!=baseline[key] for key in ['version','effective_date','parameters','rules']):return False
        elif name=='get_master_item':
            item=result['item']
            if data.items.get(item['item_code'])!=item:return False
        elif name=='search_catalog_items':
            if any(data.items.get(item['item_code'])!=item for item in result.get('items',[])):return False
        elif name=='get_supplier_details':
            supplier=result['supplier']
            if data.suppliers.get(supplier['supplier_id'])!=supplier:return False
        elif name=='get_preferred_suppliers':
            # Rankings can incorporate user-imported history. Keep them local
            # until the complete input snapshot has approved provenance.
            return False
        elif name=='get_contract_details':
            contract=result['contract'];known=next((c for c in data.contracts if c['contract_id']==contract['contract_id']),None)
            if not known or any(contract.get(key)!=known[key] for key in ['contract_id','supplier_id','start_date','end_date','value_cap','lines']):return False
        elif name in {'get_decision_evidence','get_purchase_request'}:
            # A public-looking PR prefix does not establish provenance for its
            # descriptions, policy amendment, requester or valuation inputs.
            return False
        else:return False
    return bool(tool_outputs)

def model_evidence(outputs):
    values=deepcopy(outputs)
    for output in values:
        result=output['result']
        record=result.get('requirement')
        if record:
            record.pop('lines',None);record.pop('approval_votes',None)
        # Buyer free-text and extracted private source text do not belong in a
        # model context even when a structured demo record is otherwise valid.
        for candidate in [result,result.get('contract',{}),record or {}]:
            for key in ['provenance','source_text','actor','requester','reason_override','buyer_reason']:candidate.pop(key,None)
    return values

def citations_for(outputs,session_id):
    sources=[]
    for output in outputs:
        result=output['result'];name=output['tool']
        matches=result.get('matches')
        if matches is not None:
            sources.extend(entry['citation'] for entry in matches);continue
        source_id='TOOL-'+digest(output)[:24]
        policy=result.get('policy',{})
        title=name.replace('_',' ').capitalize()
        if policy:title='Procurement policy '+policy['version']
        if result.get('contract'):title='Contract '+result['contract']['contract_id']
        if result.get('supplier'):title='Supplier '+result['supplier']['supplier_id']
        if result.get('requirement'):title='Decision '+result['requirement_id']
        sources.append(Citation(id=source_id,title=title,source_type='live_record',source_id=source_id,policy_version=policy.get('version') or result.get('policy_version'),clause=None,page=None,effective_date=policy.get('effective_date'),content_hash=output['source_hash'],excerpt=json.dumps(result,default=str)[:1800],href='/api/chat/sessions/'+session_id+'/sources/'+source_id).model_dump())
    return list({source['id']:source for source in sources}.values())

def local_answer(intent,outputs):
    """Useful evidence display when external synthesis is disabled/unavailable."""
    if not outputs:return 'I do not have enough authorized evidence to answer that. Specify an item, contract, policy version, or both the run ID and requirement ID.'
    result=outputs[0]['result'];name=outputs[0]['tool']
    if name=='get_active_policy':
        p=result['policy']
        return policy_text(p,result['as_of_date'])
    if result.get('matches'):
        passages=[passage_text(entry['content']) for entry in result['matches']]
        return 'From the applicable sources:\n\n'+'\n\n'.join('- '+text for text in dict.fromkeys(passages) if text)
    if name in {'search_policy_clauses','search_contracts'}:return 'I could not find an applicable approved source for that question. Specify the policy version or exact contract ID; I will not infer a missing rule.'
    if name=='get_contract_details':
        c=result['contract']
        return f"Contract {c['contract_id']} is {'within' if c['valid_as_of'] else 'outside'} its validity dates as of {result['as_of_date']}. Its current remaining ceiling is INR {c['remaining_value']}. The contract details show its dates, supplier status and rates."
    if name=='get_supplier_details':
        s=result['supplier'];return f"Supplier {s['supplier_id']} ({s['name']}) is {s['status']}. Supplier selection must still satisfy the effective policy; status alone does not authorize a purchase."
    if name=='get_preferred_suppliers':return f"The backend returned {len(result['suppliers'])} eligible ranked supplier relationships for {result['item_code']} as of {result['as_of_date']}. The scores and price references below are the actual calculation results."
    if name in {'get_decision_evidence','get_purchase_request'}:
        r=result['requirement'];return f"Requirement {r['id']} was recommended as {r['route']} under policy {r['policy_version']}: {r['reason']} Its approval status is {r['approval_status']}. Inspect the evidence below for the exact grouping, value, contract evaluation and supplier selection."
    if name=='compare_policy_versions':return f"There are {len(result['changes'])} structured changes between {result['version_a']} ({result['status_a']}) and {result['version_b']} ({result['status_b']}). These are configuration differences; a draft is not an enforced policy."
    if name=='search_catalog_items':return 'These are the catalog matcher’s actual candidates. Incomplete technical specifications require clarification before an exact item can be selected.'
    if name=='get_master_item':return 'This is the authoritative catalog specification and unit. Confirm that its technical details match what you need.'
    return 'These are the authorized backend records for your question. No purchasing action has been taken.'

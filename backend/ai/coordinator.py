"""Lease-based chat orchestration; network calls never hold database locks.

The only write tool is an explicit, locally validated purchase confirmation.
All model-selected tools are reads. Finalization checks ownership, lease and
revision again, making retries safe across workers rather than process-local.
"""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import uuid4
import json,re,time
from fastapi import HTTPException
from sqlalchemy import select
from ..db import Chat,ChatTurn,ChatMessage,now
from ..domain import digest
from ..service import current_data,execute_run,audit
from ..chat import parse_message
from .config import settings
from .safety import ExternalContext,PrivacyBoundaryError,assert_external_allowed,authorize_actor
from .provider import Provider,ProviderUnavailable
from .budget import BudgetExceeded
from .schemas import IntentPlan,GroundedAnswer
from .intent import local_intent,conversational_reply,QUESTION_INTENTS,validate_updates,validate_draft
from .prompts import INTENT_PROMPT,ANSWER_PROMPT
from .tools import execute,definitions,today
from .grounding import provenance,model_evidence,citations_for,local_answer,validate_answer,display_answer

LEASE_SECONDS=240

def _reserve(factory,lock,body,actor):
    session_id=body.session_id or 'CHAT-'+uuid4().hex
    request_id=body.request_id or uuid4().hex
    turn_id='TURN-'+digest([str(actor),request_id])[:40]
    request_hash=digest([body.session_id,body.message,body.action,body.expected_revision,body.demo_data_acknowledged])
    with lock,factory.begin() as session:
        authorize_actor(session,actor)
        prior=session.get(ChatTurn,turn_id)
        if prior:
            if prior.request_hash!=request_hash:raise HTTPException(409,'Request ID was already used for a different message')
            if prior.status=='completed':return None,None,None,deepcopy(prior.response)
            raise HTTPException(409,'This message is pending or expired; retrieve the session before retrying with a new request ID')
        record=session.scalar(select(Chat).where(Chat.id==session_id).with_for_update())
        if body.session_id and not record:raise HTTPException(404,'Chat session not found')
        payload=deepcopy(record.payload) if record else {'actor':str(actor),'messages':[],'state':{},'revision':0}
        if payload['actor']!=str(actor):raise HTTPException(403,'This session belongs to another actor')
        if len(payload['messages'])>=400:raise HTTPException(409,'Chat session limit reached; start a new session')
        revision=payload.get('revision',0)
        if body.expected_revision is not None and revision!=body.expected_revision:raise HTTPException(409,'Chat changed; retrieve the current session before sending again')
        if payload.get('active_turn') and payload.get('lease_until',0)>time.time():raise HTTPException(409,'Another message is still being processed')
        if payload.get('active_turn'):
            expired=session.get(ChatTurn,payload['active_turn'])
            if expired:expired.status='expired'
        payload.update(active_turn=turn_id,lease_until=int(time.time())+LEASE_SECONDS)
        if record:record.payload=payload
        else:session.add(Chat(id=session_id,payload=payload))
        session.flush()
        session.add(ChatTurn(id=turn_id,chat_id=session_id,actor=str(actor),request_hash=request_hash,revision=revision,status='pending',expires_at=payload['lease_until'],response=None,payload={}))
    return session_id,turn_id,payload,None

def _local_tools(message,intent,data):
    """Conservative defaults also make live knowledge work without a provider."""
    args={};name='search_policy_clauses'
    if intent=='policy_question':
        name='get_active_policy' if re.search(r'\b(?:current|active|effective) (?:procurement |purchasing )?policy\b',message,re.I) else 'search_policy_clauses'
    elif intent=='contract_question':
        ids=[c['contract_id'] for c in data.contracts if c['contract_id'].casefold() in message.casefold()]
        name='get_contract_details' if len(ids)==1 else 'search_contracts'
        if len(ids)==1:args={'contract_id':ids[0]}
    elif intent=='supplier_question':
        suppliers=[sid for sid in data.suppliers if re.search(r'(?<![\w-])'+re.escape(sid)+r'(?![\w-])',message,re.I)]
        items=[code for code in data.items if re.search(r'(?<![\w-])'+re.escape(code)+r'(?![\w-])',message,re.I)]
        if len(suppliers)==1:name='get_supplier_details';args={'supplier_id':suppliers[0]}
        elif len(items)==1:name='get_preferred_suppliers';args={'item_code':items[0]}
        else:return []
    elif intent=='decision_explanation':
        run=re.search(r'\bRUN-[A-Za-z0-9-]+',message);req=re.search(r'\bREQ-[A-Za-z0-9-]+',message)
        if not run or not req:return []
        name='get_decision_evidence';args={'run_id':run[0],'requirement_id':req[0]}
    if name.startswith('search_'):args={'query':message}
    return [{'name':name,'arguments':args}]

def _compute(factory,body,actor,payload,session_id):
    with factory() as session:
        authorize_actor(session,actor);data=current_data(session)
    state=deepcopy(payload.get('state',{}));intent=local_intent(body.message,state)
    from ..proposals import handoff
    from ..security import role_of
    proposal=handoff(state,body.message,role_of(actor)) if body.action=='message' else None
    if proposal:return proposal[0],proposal[1],'policy_proposal','knowledge',[],[],False,[],'local_only',False
    state.pop('policy_proposal_text',None)
    if body.action=='message':
        guidance=conversational_reply(body.message,state)
        if guidance is not None:
            return state,guidance,'general_procurement_question',payload.get('mode','intake'),[],[],False,[],'local_only',False
    if body.action=='confirm':intent='confirm_purchase_request'
    if body.action=='cancel':intent='cancel_purchase_request'
    status='local_only';plan=None;outputs=[];followups=[]
    context=ExternalContext(body.demo_data_acknowledged,('fictional_demo',),True)
    provider=Provider(factory,actor);external=False
    try:
        assert_external_allowed(context,body.message);external=settings().enabled
    except PrivacyBoundaryError:pass
    # Never send prior messages or draft free text that may have been local-only.
    # Each turn has its own explicit input acknowledgement and independent evidence.
    if external and intent in QUESTION_INTENTS:status='available'
    if external and intent not in QUESTION_INTENTS|{'confirm_purchase_request','cancel_purchase_request','unsupported'}:
        try:
            plan=provider.structured([{'role':'system','content':INTENT_PROMPT},{'role':'user','content':json.dumps({'today':today().isoformat(),'message':body.message,'draft_fields_present':list(state)})}],IntentPlan,context).value
            # Consent cannot be generated by a language model.
            if plan.intent not in {'confirm_purchase_request','cancel_purchase_request'} and intent not in QUESTION_INTENTS:intent=plan.intent
            status='available'
        except (ProviderUnavailable,PrivacyBoundaryError,BudgetExceeded):status='unavailable_local_fallback'
    if intent=='cancel_purchase_request':return {},'Draft cancelled. No purchase request was created.',intent,'intake',[],[],False,[],status,False
    if intent=='confirm_purchase_request':
        valid=validate_draft(state,data)
        eligible=(body.action=='confirm' or payload.get('mode')=='intake') and valid['ready']
        reply='Confirmation requires a complete purchase draft. Provide the missing details first.' if not eligible else 'Confirming the validated draft.'
        return valid,reply,intent,('intake' if eligible else payload.get('mode','intake')),[],[],False,[],status,eligible
    if intent=='unsupported':return state,'I can explain records and prepare a purchase draft. Approvals, policy activation and changes to master data require their authorized workspace actions.',intent,'knowledge',[],[],False,[],status,False
    if intent not in QUESTION_INTENTS:
        if plan:
            state,warnings=validate_updates(state,plan,body.message,data)
            reply=('Please clarify: '+ '; '.join(warnings)) if warnings else ('Review the complete, server-validated draft and select Confirm PR.' if state['ready'] else (plan.clarification or 'Please provide '+', '.join(state['missing_fields']).replace('_',' ')+'.'))
        else:
            state,reply=parse_message(state,body.message,data);state=validate_draft(state,data)
        return state,reply,intent,'intake',[],[],False,[],status,False
    calls=_local_tools(body.message,intent,data)
    allowed={
        'policy_question':{'get_active_policy','search_policy_clauses','compare_policy_versions'},
        'contract_question':{'search_contracts','get_contract_details','get_supplier_details'},
        'supplier_question':{'get_preferred_suppliers','get_supplier_details','search_catalog_items'},
        'decision_explanation':{'get_decision_evidence','get_purchase_request'},
        'general_procurement_question':{'search_policy_clauses','get_recent_user_requests','search_catalog_items','get_master_item'},
    }[intent]
    direct_policy=bool(calls and calls[0]['name']=='get_active_policy')
    if external and status=='available' and settings().max_iterations>=2 and not direct_policy:
        try:
            planned=provider.tool_calls([{'role':'system','content':INTENT_PROMPT+' Choose only relevant read-only tools. Intent: '+intent+'. Today is '+today().isoformat()+'. Use exact identifiers in the user message.'},{'role':'user','content':body.message}],definitions(allowed),context)
            planned=[call for call in planned if call['name'] in allowed]
            if planned:calls=planned
        except (ProviderUnavailable,PrivacyBoundaryError,BudgetExceeded):status='unavailable_local_fallback'
    used=set()
    for call in calls[:settings().max_tools]:
        name=call['name']
        try:
            if name not in allowed:continue
            args=json.loads(call['arguments']) if isinstance(call['arguments'],str) else call['arguments']
            # Exact identity and historical date claims need literal evidence.
            for key in ['item_code','supplier_id','contract_id','run_id','requirement_id','policy_version','version_a','version_b']:
                if args.get(key) and str(args[key]).casefold() not in body.message.casefold():raise ValueError('Identifier not supplied by user')
            if args.get('as_of_date') and args['as_of_date'] not in body.message:args['as_of_date']=None
            key=digest([name,args])
            if key in used:continue
            used.add(key)
            output=execute(factory,actor,name,args)
            # PostgreSQL retrieval is already real RAG. Spend free-tier query
            # embeddings only when lexical retrieval found no matching source.
            if external and name in {'search_policy_clauses','search_contracts'} and not output['result'].get('matches'):
                try:embedding=provider.embed([body.message],context,task_type='RETRIEVAL_QUERY')[0]
                except (ProviderUnavailable,PrivacyBoundaryError,BudgetExceeded):embedding=None
                if embedding:output=execute(factory,actor,name,args,query_embedding=embedding,embedding_model=settings().embedding_model)
            outputs.append(output)
        except (ValueError,HTTPException,KeyError,TypeError):continue
    if not outputs:
        for call in _local_tools(body.message,intent,data):
            try:outputs.append(execute(factory,actor,call['name'],call['arguments']))
            except (ValueError,HTTPException,KeyError,TypeError):pass
    citations=citations_for(outputs,session_id);reply=local_answer(intent,outputs);grounded=bool(citations)
    if external and status=='available' and (not provenance(outputs) or settings().max_iterations<3):status='local_evidence'
    if external and status=='available' and provenance(outputs):
        evidence=model_evidence(outputs)
        try:
            answer=provider.structured([{'role':'system','content':ANSWER_PROMPT},{'role':'user','content':json.dumps({'question':body.message,'evidence':evidence,'citations':citations},default=str)}],GroundedAnswer,context).value
            if validate_answer(answer,citations,evidence):
                reply=display_answer(answer.answer);followups=answer.suggested_followups;grounded=not answer.insufficient_evidence
                citations=[c for c in citations if c['id'] in answer.citation_ids]
            else:status='invalid_answer_local_fallback'
        except (ProviderUnavailable,PrivacyBoundaryError,BudgetExceeded):status='unavailable_local_fallback'
    return state,reply,intent,'knowledge',citations,[o['tool'] for o in outputs],grounded,followups,status,False

def respond(factory,lock,body,actor):
    session_id,turn_id,snapshot,cached=_reserve(factory,lock,body,actor)
    if cached is not None:return cached
    try:
        state,reply,intent,mode,citations,tools,grounded,followups,status,confirm=_compute(factory,body,actor,snapshot,session_id)
        with lock,factory.begin() as session:
            authorize_actor(session,actor)
            record=session.scalar(select(Chat).where(Chat.id==session_id).with_for_update());payload=deepcopy(record.payload)
            turn=session.get(ChatTurn,turn_id)
            if payload.get('active_turn')!=turn_id or payload.get('revision',0)!=turn.revision or time.time()>turn.expires_at:raise HTTPException(409,'Chat changed or turn expired; retrieve the current session')
            result=None
            if confirm:
                state=validate_draft(state,current_data(session))
                if not state['ready']:raise HTTPException(409,'Draft is no longer valid; review it before confirming')
                item=current_data(session).items.get(state['item_code'],{});submission=int(payload.get('submission_count',0))+1
                row={'pr_no':f'PR-CHAT-{session_id[-12:].upper()}-{submission:04d}','pr_line':'1','created_at':datetime.now(ZoneInfo('Asia/Kolkata')).replace(tzinfo=None).isoformat(timespec='seconds'),'requester':str(actor),'department':'Chat intake','plant':state['plant'],'item_code':'' if state['item_code']=='NEW' else state['item_code'],'description':item.get('description',state.get('description','')),'quantity':state['quantity'],'uom':state['uom'],'estimated_unit_price':state.get('estimated_unit_price',''),'need_by_date':state['need_by_date'],'urgency':state['urgency']}
                result=execute_run(session,[row],None,actor)
                if result['issues']:reply='Request validation failed. Correct the draft before confirming again.'
                else:reply='PR created. '+result['rows'][0]['reason'];state={};payload['submission_count']=submission
            messages=[{'role':'user','content':body.message,'timestamp':now()},{'role':'assistant','content':reply,'timestamp':now(),'citations':citations,'grounded':grounded,'mode':mode}]
            payload['messages'].extend(messages)
            payload.update(state=state,mode=mode,revision=turn.revision+1,active_turn=None,lease_until=0)
            # Bounded source snapshots are owner-only and served through auth.
            sources=dict(payload.get('sources',{}));sources.update({c['id']:c for c in citations});payload['sources']=dict(list(sources.items())[-64:])
            response={'session_id':session_id,'message':reply,'state':state,'alternatives':state.get('alternatives',[]),'run':result,'messages':payload['messages'],'intent':intent,'mode':mode,'citations':citations,'tools_used':tools,'grounded':grounded,'followups':followups,'revision':payload['revision'],'ai_status':status}
            record.payload=payload;turn.status='completed';turn.response=response
            for message in messages:session.add(ChatMessage(id=uuid4().hex,chat_id=session_id,payload=message))
            audit(session,actor,'chat.message',{'session_id':session_id,'mode':mode,'tools':tools,'ai_status':status,'pr_created':bool(result and not result['issues'])})
        return response
    except Exception:
        # Clear only our lease; a newer worker's revision must never be removed.
        with lock,factory.begin() as session:
            record=session.scalar(select(Chat).where(Chat.id==session_id).with_for_update());turn=session.get(ChatTurn,turn_id)
            if record and record.payload.get('active_turn')==turn_id:
                record.payload={**record.payload,'active_turn':None,'lease_until':0}
            if turn and turn.status=='pending':turn.status='failed'
        raise

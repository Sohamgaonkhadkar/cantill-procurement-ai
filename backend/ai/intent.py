"""Conservative local routing and independent validation of model field updates."""
from datetime import date,datetime
from zoneinfo import ZoneInfo
from copy import deepcopy
import re
from ..domain import number
from ..chat import parse_message
from ..matching import resolve,normalize,specs,model_tokens
from .schemas import IntentPlan

QUESTION_INTENTS={'policy_question','contract_question','supplier_question','decision_explanation','general_procurement_question'}

def conversational_reply(message,state):
    """Handle whole social/help turns locally without changing drafts or consent.

    Whole-turn matches leave substantive follow-up questions and purchases on
    the ordinary, validated knowledge/intake paths.
    """
    text=re.sub(r'\s+',' ',message.casefold()).strip().rstrip('.!?')
    if re.fullmatch(r'(?:thanks(?: a lot| so much)?|thank you(?: very much)?|thx|ty|cheers|ok(?:ay)?|got it|understood)(?:[, ]+(?:thanks|thank you))?',text):
        if state.get('ready'):
            return "You're welcome. Your draft is unchanged. Review it and select Confirm and create PR when you are ready; this message has not created a request."
        return "You're welcome. You can continue your purchase draft or ask about a policy, supplier or contract."
    greeting=bool(re.fullmatch(r'(?:hi|hello|hey|good morning|good afternoon|good evening)(?: corvo)?',text))
    help_request=bool(re.fullmatch(r'(?:help|help me|what can you do|how (?:do i|can i) (?:start|use (?:this|the chatbot)|create (?:a |my )?(?:pr|purchase request))|(?:what|which) (?:details|information|fields) (?:do you need|should i provide))',text))
    echoed_prompt=bool(re.fullmatch(r'tell me the item or specification, quantity, plant, need-by date and whether this is normal or emergency',text))
    if not (greeting or help_request or echoed_prompt):return None
    if state.get('ready'):
        return 'Your purchase draft is complete. Review the specification panel, send any corrections, or select Confirm and create PR. No request is created until you confirm.'
    guidance='Describe what you want to buy: item code or specification, quantity, plant, need-by date and Normal or Emergency urgency. These details must come from you; I will not invent them.'
    missing=state.get('missing_fields',[])
    if missing:guidance+=' Your draft still needs: '+', '.join(field.replace('_',' ') for field in missing)+'.'
    else:guidance+=' You can also ask a specific policy, supplier or contract question.'
    return ('Hello. ' if greeting else '')+guidance


def local_intent(message,state):
    text=message.lower().strip()
    if re.fullmatch(r'(?:cancel|reset|cancel (?:the |my )?(?:request|draft))',text):return 'cancel_purchase_request'
    if text in {'confirm','yes','submit'}:return 'confirm_purchase_request'
    if re.search(r'\b(?:approve|activate|override|delete|execute|run sql|change supplier status)\b',text) and not text.endswith('?'):return 'unsupported'
    if re.match(r'^(?:can|could|would) you (?:please )?(?:help me )?(?:buy|order|request|prepare|create|raise)\b',text):
        return 'correct_purchase_request' if state else 'create_purchase_request'
    question=bool(re.search(r'\b(?:what|which|when|why|how|explain|show|list|can|tell me)\b',text) or '?' in text)
    if question:
        if any(word in text for word in ['decision','this pr','this request','grouped','benchmark','rejected']):return 'decision_explanation'
        if any(word in text for word in ['supplier','vendor','preferred']):return 'supplier_question'
        if 'contract' in text:return 'contract_question'
        if any(word in text for word in ['policy','limit','threshold','rfq','rfp','emergency','capital','group','blocked']):return 'policy_question'
        return 'general_procurement_question'
    return 'correct_purchase_request' if state else 'create_purchase_request'

SMALL={word:i for i,word in enumerate(['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen'])}
TENS={word:10*(i+2) for i,word in enumerate(['twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety'])}

def spoken_number(fragment):
    fragment=re.sub(r'\b\d{4}-\d{2}-\d{2}\b',' ',fragment)
    numeric=re.search(r'(?<![\w.])[+-]?\d[\d,]*(?:\.\d+)?(?:e[+-]?\d+)?',fragment,re.I)
    if numeric:return number(numeric[0])
    words=re.findall(r'[a-z]+',fragment.lower());total=0;part=0;seen=False
    for word in words:
        if word in SMALL:part+=SMALL[word];seen=True
        elif word in TENS:part+=TENS[word];seen=True
        elif word=='dozen':part=max(1,part)*12;seen=True
        elif word=='hundred':part=max(1,part)*100;seen=True
        elif word in {'thousand','lakh','million'}:total+=max(1,part)*{'thousand':1000,'lakh':100000,'million':1000000}[word];part=0;seen=True
    if not seen:raise ValueError('No quantity evidence')
    return number(total+part)

def _literal(fragment,message):return bool(fragment and fragment.casefold() in message.casefold())

def validate_updates(state,plan,message,data):
    state=deepcopy(state);state.setdefault('description','')
    updates=plan.updates.model_dump(exclude_none=True);evidence=plan.evidence.model_dump(exclude_none=True)
    warnings=[]
    for field in plan.clear_fields:
        if _literal(evidence.get(field),message) and re.search(r'\b(?:not|cancel|remove|replace|instead|wrong|other)\b',evidence[field],re.I):state.pop(field,None)
    # Negative technical references invalidate a prior SKU independently of
    # what the model chose. An exact replacement still needs positive evidence.
    old=data.items.get(state.get('item_code',''),{})
    for token in re.findall(r'\b\d+(?:[-/][A-Za-z0-9]+)+\b',old.get('description','')):
        if re.search(r'\bnot\s+(?:the\s+)?'+re.escape(token)+r'\b',message,re.I):state.pop('item_code',None)
    for token in model_tokens(old.get('description','')):
        if re.search(r'\bnot\s+(?:the\s+)?'+re.escape(token)+r'\b',normalize(message),re.I):state.pop('item_code',None)
    for field,value in updates.items():
        fragment=evidence.get(field)
        if not _literal(fragment,message):warnings.append(field+' has no literal user evidence');continue
        if field in {'quantity','estimated_unit_price'}:
            try:
                candidate=spoken_number(value) if field=='quantity' and re.fullmatch(r'[A-Za-z -]+',value) else number(value)
                if candidate<=0 or candidate!=spoken_number(fragment):raise ValueError()
                state[field]=str(candidate)
            except ValueError:state.pop(field,None);warnings.append('Provide a positive, supported '+field.replace('_',' '))
        elif field=='item_code':
            if value=='NEW':
                if re.search(r'\bnew (?:item|product|material)\b',message,re.I):state['item_code']='NEW'
                else:warnings.append('A new item must be explicitly requested')
            elif value not in data.items:warnings.append('Unknown item code')
            elif re.search(r'(?<![\w-])'+re.escape(value)+r'(?![\w-])',message,re.I):state['item_code']=value
            else:
                resolved,match=resolve('',updates.get('description',fragment),'',data.items)
                if resolved==value and not match.get('error'):state['item_code']=value
                else:state.pop('item_code',None);warnings.append('Select the exact catalog specification before continuing')
        elif field=='plant':
            if value not in data.plants:warnings.append('Unknown plant')
            else:
                names=[value,*normalize(data.plants[value]['name']).split()]
                if any(len(name)>2 and re.search(r'\b'+re.escape(name)+r'\b',fragment,re.I) for name in names):state['plant']=value
                else:warnings.append('Plant is not supported by the user text')
        elif field=='need_by_date':
            try:
                expected,_=parse_message({},fragment,data)
                explicit=re.search(r'\b\d{4}-\d{2}-\d{2}\b',fragment)
                candidate=date.fromisoformat(value)
                supported=explicit and explicit[0]==value or expected.get('need_by_date')==value
                if not supported or candidate<datetime.now(ZoneInfo('Asia/Kolkata')).date():raise ValueError()
                state[field]=value
            except ValueError:state.pop(field,None);warnings.append('Clarify the need-by date')
        elif field=='urgency':
            parsed,_=parse_message({},fragment,data)
            if parsed.get('urgency')==value:state[field]=value
            else:warnings.append('Clarify Normal versus Emergency urgency')
        elif field=='uom':
            allowed={item['uom'].upper() for item in data.items.values()}|{'NOS','PAIR','KG','MTR','LTR','SET'}
            aliases={'NOS':['nos','units','pieces','piece'],'PAIR':['pair','pairs'],'KG':['kg','kilogram','kilograms'],'MTR':['mtr','metres','meters','metre','meter'],'LTR':['ltr','litres','liters','litre','liter'],'SET':['set','sets']}
            canonical=next((key for key,words in aliases.items() if value.casefold() in words),value.upper())
            if canonical in allowed and any(re.search(r'\b'+re.escape(word)+r'\b',fragment,re.I) for word in aliases.get(canonical,[value])):state['uom']=canonical
            else:warnings.append('Unsupported unit of measure')
        elif field=='description':state['description']=value[:1000] if value.casefold() in fragment.casefold() else fragment[:1000]
    # Explicit catalog IDs are deterministic user evidence even when a language
    # model omits them. This never resolves an incomplete description to a SKU.
    mentioned=[]
    for code in data.items:
        if not re.search(r'(?<![\w-])'+re.escape(code)+r'(?![\w-])',message,re.I):continue
        negative=re.search(r"\b(?:not|except|exclude|avoid|without|don't\s+use|do\s+not\s+use)\s+(?:(?:the|item|that)\s+)?"+re.escape(code)+r'(?![\w-])',message,re.I)
        if not negative:mentioned.append(code)
        elif state.get('item_code')==code:state.pop('item_code',None)
    selected=[code for code in mentioned if re.search(r'\b(?:use|select|choose)\s+(?:item\s+)?'+re.escape(code)+r'(?![\w-])',message,re.I)]
    if len(mentioned)==1:state['item_code']=mentioned[0]
    elif len(mentioned)>1:
        if len(selected)==1:state['item_code']=selected[0]
        else:state.pop('item_code',None);warnings.append('Select exactly one catalog item for this draft')
    return validate_draft(state,data),warnings

def validate_draft(state,data):
    state=deepcopy(state);state.setdefault('description','')
    code=state.get('item_code')
    if code and code!='NEW':
        if code not in data.items:state.pop('item_code',None)
        else:state['uom']=data.items[code]['uom']
    if state.get('plant') not in data.plants:state.pop('plant',None)
    if state.get('urgency') not in {'Normal','Emergency'}:state.pop('urgency',None)
    if state.get('need_by_date'):
        try:
            if date.fromisoformat(state['need_by_date'])<datetime.now(ZoneInfo('Asia/Kolkata')).date():raise ValueError()
        except (ValueError,TypeError):state.pop('need_by_date',None)
    for field in ['quantity','estimated_unit_price']:
        if state.get(field):
            try:
                if number(state[field])<=0:raise ValueError()
            except ValueError:state.pop(field,None)
    needed=['item_code','quantity','plant','need_by_date','urgency']
    if state.get('item_code')=='NEW':needed+=['uom','estimated_unit_price']
    state['missing_fields']=[field for field in needed if not state.get(field)]
    state['ready']=not state['missing_fields']
    return state

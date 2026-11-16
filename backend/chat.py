from datetime import datetime,timedelta,date
from zoneinfo import ZoneInfo
import re
from .matching import normalize,specs,model_tokens
from .domain import digest,number

NUMERIC=r'[+-]?\d[\d,]*(?:\.\d+)?(?:e[+-]?\d+)?'
QUANTITY=r'\b(?:need|quantity|qty|around|about|make it)\s*(?:is|to|:|=)?\s*('+NUMERIC+r')\b(?![-/][a-z0-9])(?!\s*(?:inch|mm|hp|kw|gb|tons?)\b)'
UNITS=r'(?<![\w.])('+NUMERIC+r')\s*(?:units?|pieces?|nos|pairs?|kg|ltr|litres?|meters?|mtr)\b'

def specification_text(text,data):
    text=re.sub(QUANTITY,' ',text,flags=re.I)
    text=re.sub(UNITS,' ',text,flags=re.I)
    text=re.sub(r'\b\d{4}-\d{2}-\d{2}\b|\bin\s+\d+\s+days?\b',' ',text,flags=re.I)
    for pid in data.plants:text=re.sub(r'\b'+re.escape(pid)+r'\b',' ',text,flags=re.I)
    return text

def parse_message(state,message,data):
    state=dict(state); state.setdefault('description','')
    text=message.lower()
    if re.search(r'\b(cancel|reset)\b',text): return {},'Cancelled. Describe your next purchase request.'
    if 'new item' in text:
        state['item_code']='NEW'; state['ready']=False
        state['description']=message; state.pop('estimated_unit_price',None); state.pop('uom',None)
    if re.search(r'\b(?:normal|routine)\b|\bnot\s+(?:urgent|(?:an?\s+)?emergency)\b',text): state['urgency']='Normal'
    elif re.search(r'\bemergency|\burgent\b',text): state['urgency']='Emergency'
    estimate=re.search(r'(?:price|estimate)\s*(?:is|:|=)?\s*('+NUMERIC+r')',text)
    if estimate and (state.get('item_code')=='NEW' or 'new item' in text):
        try:
            value=number(estimate[1])
            if value<=0:raise ValueError()
            state['estimated_unit_price']=str(value)
        except ValueError:
            state.pop('estimated_unit_price',None);state['ready']=False
            return state,'Please provide a positive, finite estimated unit price in INR.'
    mentioned=[]
    for pid,plant in data.plants.items():
        names=[pid.lower()]+[x for x in normalize(plant['name']).split() if len(x)>4 and x!='plant']
        found=any(re.search(r'\b'+re.escape(n)+r'\b',text) for n in names)
        negated=any(re.search(r'\b(?:not|instead of)\s+(?:plant\s+)?'+re.escape(n)+r'\b',text) for n in names)
        if found and not negated:mentioned.append(pid)
        elif negated and state.get('plant')==pid:state.pop('plant',None)
    if len(mentioned)>1:
        state.pop('plant',None);state['ready']=False
        return state,'I found multiple plants. Choose one plant for this request: '+', '.join(mentioned)
    if mentioned:state['plant']=mentioned[0]
    quantity=re.search(QUANTITY,text)
    if not quantity: quantity=re.search(UNITS,text)
    raw_quantity=quantity[1] if quantity else text.strip() if re.fullmatch(NUMERIC,text.strip(),re.I) else None
    if raw_quantity is not None:
        try:
            value=number(raw_quantity)
            if value<=0:raise ValueError()
            state['quantity']=str(value)
        except ValueError:
            state.pop('quantity',None);state['ready']=False
            return state,'Quantity must be a positive, finite number within the supported range.'
    elif re.search(r'\b(?:quantity|qty)\b',text):
        state.pop('quantity',None);state['ready']=False
        return state,'Please enter a positive numeric quantity.'
    today=datetime.now(ZoneInfo('Asia/Kolkata')).date()
    if state.get('item_code')=='NEW':
        aliases={'nos':'NOS','units':'NOS','unit':'NOS','pieces':'NOS','piece':'NOS','pair':'PAIR','pairs':'PAIR','kg':'KG','mtr':'MTR','metres':'MTR','meters':'MTR','ltr':'LTR','litres':'LTR','liters':'LTR','set':'SET','sets':'SET'}
        for word,uom in aliases.items():
            if re.search(r'\b'+word+r'\b',text): state['uom']=uom; break
    exact=re.search(r'\b(\d{4}-\d{2}-\d{2})\b',text)
    if exact:
        try: state['need_by_date']=date.fromisoformat(exact[1]).isoformat()
        except ValueError:
            state.pop('need_by_date',None); state['ready']=False
            return state,'That date is invalid. Use YYYY-MM-DD.'
    elif 'tomorrow' in text: state['need_by_date']=(today+timedelta(days=1)).isoformat()
    elif re.search(r'\btoday\b',text): state['need_by_date']=today.isoformat()
    elif relative:=re.search(r'\bin\s+(\d+)\s+days?\b',text):
        if len(relative[1])>4 or int(relative[1])>3650:
            state.pop('need_by_date',None); state['ready']=False
            return state,'Use a need-by date within the next 3650 days or an explicit YYYY-MM-DD date.'
        state['need_by_date']=(today+timedelta(days=int(relative[1]))).isoformat()
    else:
        for day,name in enumerate(['monday','tuesday','wednesday','thursday','friday','saturday','sunday']):
            if name in text:
                delta=(day-today.weekday())%7 or 7
                if 'next '+name in text and today.weekday()<day: delta+=7
                state['need_by_date']=(today+timedelta(days=delta)).isoformat()
    known=[key for key in data.items if re.search(r'\b'+re.escape(key)+r'\b',message,re.I)]
    selected=None
    for key in known:
        if re.search(r'\b(?:to|use|select|choose)\s+(?:item\s+)?'+re.escape(key)+r'\b',message,re.I):selected=key
    if len(known)>1 and selected is None:
        state.pop('item_code',None);state['ready']=False
        return state,'I found multiple item codes. Select exactly one intended catalog item.'
    if len(known)==1 and re.search(r'\bnot\s+(?:item\s+)?'+re.escape(known[0])+r'\b',message,re.I):
        state.pop('item_code',None);state['ready']=False
        return state,'Which item should replace the excluded code?'
    selected=selected or (known[0] if known else None)
    code=(selected,) if selected else re.search(r'ITM-\d+',message,re.I)
    if code and code[0].upper() not in data.items:
        state.pop('item_code',None); state['ready']=False
        return state,'That item code is not in the master. Select a valid code or describe a new item explicitly.'
    if code and code[0].upper() in data.items: state['item_code']=code[0].upper()
    explicit_item_change=bool(re.search(r'\b(?:change|replace|correct)\b.*\b(?:item|product|material)\b',text))
    if explicit_item_change and not (code and code[0].upper() in data.items):
        state.pop('item_code',None); state['ready']=False
        state['description']=message
        state.pop('alternatives',None)
    # Accumulate specification-bearing messages, never quantity/date-only replies.
    if any(t in text for t in ['need','bearing','brg','glove','hose']) or (not quantity and not exact and not any(k in text for k in ['confirm','normal','emergency'])):
        state['description']=(state['description']+' '+message).strip()
    # Reconsider a clearly described item in every turn. Looking only while the
    # item field is empty silently ignores corrections after confirmation-ready.
    for query_text in [message,state['description']+' '+message]:
        query=normalize(specification_text(query_text,data)); qwords=set(query.split()); qspecs=specs(query)
        candidates=[]
        for key,item in data.items.items():
            target=normalize(item['description']); words=set(target.split()); numeric=specs(target)
            # Protect model suffixes during conversational matching as well as
            # batch matching. Quantity, dates and plant codes are context, but
            # a different bearing suffix must never select a catalog model.
            models={t for t in model_tokens(query) if re.fullmatch(r'\d+[a-z]+',t) and not re.fullmatch(r'\d+(?:mm|kg|gb|kw|hp|sqmm|nos|ltr|mtr)',t)}
            if not models<=model_tokens(target): continue
            coverage=len(words&qwords)/max(1,len(words))
            if numeric and not all(n in qspecs for n in numeric): continue
            if coverage>=.5: candidates.append((coverage,key))
        candidates.sort(key=lambda x:(-x[0],x[1]))
        if candidates and candidates[0][0]>=.65 and (len(candidates)<2 or candidates[0][0]-candidates[1][0]>=.15):
            if not code:
                state['item_code']=candidates[0][1]
            state.pop('alternatives',None)
            break
        if state.get('item_code'): break
        if candidates: state['alternatives']=[{'item_code':k,'description':data.items[k]['description']} for _,k in candidates[:4]]
    missing=[k for k in ['item_code','quantity','plant','need_by_date','urgency'] if not state.get(k)]
    if missing:
        prompts={'item_code':'Which item specification? You can select a master item code, or say “new item” with its description and estimated unit price.','quantity':'How many units do you need?','plant':'Which plant? '+', '.join(data.plants),'need_by_date':'When do you need it? Use YYYY-MM-DD or a weekday.','urgency':'Is this Normal or Emergency?'}
        if 'new item' in text:
            state['item_code']='NEW'
            estimate=re.search(r'(?:price|estimate)\s*(?:is|:|=)?\s*(\d+(?:\.\d+)?)',text)
            if estimate: state['estimated_unit_price']=estimate[1]
        else: return state,prompts[missing[0]]
    if state.get('item_code')=='NEW' and not state.get('estimated_unit_price'): return state,'What is the estimated unit price in INR? Say “price 1200”.'
    if state.get('item_code')=='NEW' and not state.get('uom'): return state,'What is the unit of measure? For example NOS, PAIR, KG, MTR or LTR.'
    state['ready']=all(state.get(k) for k in ['item_code','quantity','plant','need_by_date','urgency'])
    if not state['ready']: return state,'Please provide '+', '.join(k for k in missing if not state.get(k))
    item=data.items.get(state['item_code'],{'description':state['description'],'uom':state.get('uom','NOS')})
    state['uom']=item['uom']
    return state,f"Please confirm: {state['quantity']} {item['uom']} of {item['description']}, {state['plant']}, need by {state['need_by_date']}, {state['urgency']}. Reply confirm, correct a field, or cancel."

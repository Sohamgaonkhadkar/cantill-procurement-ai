from datetime import datetime,timedelta,date
from zoneinfo import ZoneInfo
import re
from .matching import normalize,specs
from .domain import digest

def parse_message(state,message,data):
    state=dict(state); state.setdefault('description','')
    text=message.lower()
    if re.search(r'\b(cancel|reset)\b',text): return {},'Cancelled. Describe your next purchase request.'
    if re.search(r'\bnormal|\bnot urgent\b',text): state['urgency']='Normal'
    elif re.search(r'\bemergency|\burgent\b',text): state['urgency']='Emergency'
    estimate=re.search(r'(?:price|estimate)\s*(?:is|:|=)?\s*(\d+(?:\.\d+)?)',text)
    if estimate and (state.get('item_code')=='NEW' or 'new item' in text): state['estimated_unit_price']=estimate[1]
    for pid,plant in data.plants.items():
        names=[pid.lower()]+[x for x in normalize(plant['name']).split() if len(x)>4 and x!='plant']
        if any(re.search(r'\b'+re.escape(n)+r'\b',text) for n in names): state['plant']=pid
    quantity=re.search(r'\b(?:need|quantity|qty|around|about)\s*(?:is|:|=)?\s*(\d+(?:\.\d+)?)\b',text)
    if not quantity: quantity=re.search(r'\b(\d+(?:\.\d+)?)\s*(?:units?|pieces?|nos|pairs?|kg|ltr|litres?|meters?|mtr)\b',text)
    if quantity: state['quantity']=quantity[1]
    elif re.fullmatch(r'\s*\d+(?:\.\d+)?\s*',text): state['quantity']=text.strip()
    today=datetime.now(ZoneInfo('Asia/Kolkata')).date()
    exact=re.search(r'\b(\d{4}-\d{2}-\d{2})\b',text)
    if exact:
        try: state['need_by_date']=date.fromisoformat(exact[1]).isoformat()
        except ValueError: return state,'That date is invalid. Use YYYY-MM-DD.'
    elif 'tomorrow' in text: state['need_by_date']=(today+timedelta(days=1)).isoformat()
    else:
        for day,name in enumerate(['monday','tuesday','wednesday','thursday','friday','saturday','sunday']):
            if name in text:
                delta=(day-today.weekday())%7 or 7
                if 'next '+name in text and today.weekday()<day: delta+=7
                state['need_by_date']=(today+timedelta(days=delta)).isoformat()
    code=re.search(r'ITM-\d+',message,re.I)
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
        query=normalize(query_text); qwords=set(query.split()); qspecs=specs(query)
        candidates=[]
        for key,item in data.items.items():
            target=normalize(item['description']); words=set(target.split()); numeric=specs(target)
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
            state['uom']='NOS'
        else: return state,prompts[missing[0]]
    if state.get('item_code')=='NEW' and not state.get('estimated_unit_price'): return state,'What is the estimated unit price in INR? Say “price 1200”.'
    state['ready']=all(state.get(k) for k in ['item_code','quantity','plant','need_by_date','urgency'])
    if not state['ready']: return state,'Please provide '+', '.join(k for k in missing if not state.get(k))
    item=data.items.get(state['item_code'],{'description':state['description'],'uom':state.get('uom','NOS')})
    state['uom']=item['uom']
    return state,f"Please confirm: {state['quantity']} {item['uom']} of {item['description']}, {state['plant']}, need by {state['need_by_date']}, {state['urgency']}. Reply confirm, correct a field, or cancel."

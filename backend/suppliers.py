from datetime import date
from decimal import Decimal as D
from math import log1p
from .domain import number

def history_for(data,item,asof,days,active_only=True):
    return sorted([p for p in data.history if p['item_code']==item and 0<(asof-date.fromisoformat(p['po_date'])).days<=days and (not active_only or data.suppliers.get(p['supplier_id'],{}).get('status')=='Active')], key=lambda p:(p['po_date'],p['po_number'],p['supplier_id']),reverse=True)

def preferred(data,item,asof,policy):
    p=policy['parameters']; history=history_for(data,item,asof,p['preferred_days'])
    contracts=[dict(c,rate=l['rate']) for c in data.contracts for l in c['lines'] if l['item_code']==item and c['start_date']<=asof.isoformat()]
    result=[]
    max_frequency=max([sum(h['supplier_id']==sid for h in history) for sid in data.suppliers]+[1])
    for sid,s in sorted(data.suppliers.items()):
        if s['status']!='Active': continue
        ph=[h for h in history if h['supplier_id']==sid]
        ch=sorted([c for c in contracts if c['supplier_id']==sid],key=lambda c:(c['start_date'],c['contract_id']),reverse=True)
        if not ph and not ch: continue
        age=(asof-date.fromisoformat(ph[0]['po_date'])).days if ph else None
        tier=1 if age is not None and age<=p['recency_days'][0] else .5 if age is not None and age<=p['recency_days'][1] else 0
        components={'frequency':D(str(log1p(min(len(ph),p['frequency_cap']))/log1p(min(max_frequency,p['frequency_cap'])))),'recency':D(str(tier)),'contract':D(bool(ch)), 'delivery':number(s['on_time_pct'])/100,'quality':number(s['quality_rating'])/5}
        components={k:v*number(p['weights'][k]) for k,v in components.items()}
        ref=ph[0]['unit_price'] if ph else ch[0]['rate']
        result.append({'supplier_id':sid,'name':s['name'],'purchase_count':len(ph),'last_purchase':ph[0]['po_date'] if ph else None,'contract_history':bool(ch),'reference_price':str(ref),'reference_source':ph[0]['po_number'] if ph else ch[0]['contract_id'],'components':{k:str(v) for k,v in components.items()},'score':str(sum(components.values(),D(0)))})
    return sorted(result,key=lambda s:(-D(s['score']),s['supplier_id']))

def suggestions(data,item,ranking,count):
    ids=[x['supplier_id'] for x in ranking]
    extra=sorted([(sid,s) for sid,s in data.suppliers.items() if s['status']=='Active' and item['category'] in s['categories'].split(';') and sid not in ids],key=lambda x:(-(number(x[1]['on_time_pct'])/100+number(x[1]['quality_rating'])/5),-number(x[1]['on_time_pct']),x[0]))
    return (ids+[sid for sid,_ in extra])[:count]

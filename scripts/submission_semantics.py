"""Read-only independent invariants. Never imports engine, service or ranking code.

This is an audit of evidence and source records, not a second policy interpreter.
It cannot establish that an unfamiliar natural-language amendment means its DSL.
"""
from collections import Counter,defaultdict
from datetime import date,datetime
from decimal import Decimal,ROUND_HALF_UP
import hashlib,json,math

def hash_value(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def cents(value):return format(Decimal(value).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'.2f')
def identity(row):return row['pr_no'],row['pr_line']
def read(path):
    with open(path,encoding='utf-8') as source:return json.load(source)
def check(condition,message):
    if not condition:raise ValueError(message)

def ranking(master,item,asof,policy):
    """Independent implementation of documented five-factor formula for auditing."""
    p=policy['parameters'];day=date.fromisoformat(asof)
    active={sid:s for sid,s in master['suppliers'].items() if s['status']=='Active' and sid not in p.get('excluded_supplier_ids',[])}
    histories={sid:sorted([h for h in master['history'] if h['item_code']==item and h['supplier_id']==sid and 0<(day-date.fromisoformat(h['po_date'])).days<=p['preferred_days']],key=lambda h:(h['po_date'],h['po_number'],h['supplier_id']),reverse=True) for sid in active}
    maximum=max([len(h) for h in histories.values()]+[1]);result=[]
    for sid,supplier in active.items():
        history=histories[sid]
        contracts=sorted([dict(c,rate=line['rate']) for c in master['contracts'] for line in c['lines'] if line['item_code']==item and c['supplier_id']==sid and c['start_date']<=asof and sid not in p.get('contract_excluded_supplier_ids',[])],key=lambda c:(c['start_date'],c['contract_id']),reverse=True)
        if not history and not contracts:continue
        age=(day-date.fromisoformat(history[0]['po_date'])).days if history else None
        recency=1 if age is not None and age<=p['recency_days'][0] else .5 if age is not None and age<=p['recency_days'][1] else 0
        values={'frequency':Decimal(str(math.log1p(min(len(history),p['frequency_cap']))/math.log1p(min(maximum,p['frequency_cap'])))),'recency':Decimal(str(recency)),'contract':Decimal(bool(contracts)),'delivery':Decimal(supplier['on_time_pct'])/100,'quality':Decimal(supplier['quality_rating'])/5}
        score=sum((v*Decimal(str(p['weights'][key])) for key,v in values.items()),Decimal(0))
        price=history[0]['unit_price'] if history else contracts[0]['rate']
        result.append((sid,score,Decimal(price)))
    return sorted(result,key=lambda r:(-r[1],r[0]))

def validate_snapshot(inputs,outputs,snapshot,master=None):
    check(Counter(map(identity,snapshot['input']))==Counter(map(identity,inputs)),'Snapshot input identities differ from CSV')
    check(Counter(json.dumps(r,sort_keys=True) for r in snapshot['input'])==Counter(json.dumps(r,sort_keys=True) for r in inputs),'Snapshot input values differ from CSV')
    expected_hash=hash_value(sorted(inputs,key=lambda r:(r['pr_no'],r['pr_line'],hash_value(r))))
    check(snapshot['input_hash']==expected_hash,'Snapshot input hash mismatch')
    check(snapshot['output_hash']==hash_value(snapshot['rows']),'Snapshot output hash mismatch')
    # Exports neutralize spreadsheet-formula identifiers. Compare their serialized
    # text without undoing that protection in the output file.
    def exported(row):
        return {k:("'"+str(v) if str(v).lstrip(' \t\r\n').startswith(('=','+','-','@')) and k not in {'pr_line','unit_price','group_value_inr'} else str(v)) for k,v in row.items()}
    check(outputs==[exported(r) for r in snapshot['rows']],'CSV differs from its immutable snapshot')
    if master:check(hash_value(master)==snapshot['data_hash'],'Master snapshot hash differs from run data hash')
    policies={p['version']:p for p in snapshot['policy_snapshots']};members=[];groups={};allocated=defaultdict(lambda:Decimal(0))
    for requirement in snapshot['requirements']:
        rid=requirement['id'];groups[rid]=requirement
        policy=policies[requirement['policy_version']];p=policy['parameters'];lines=requirement['lines'];e=requirement['evidence'];anchor=e['group_anchor']
        anchor_time=datetime.fromisoformat(anchor['created_at']);asof=anchor_time.date().isoformat()
        check(policy['effective_date']<=asof,'Future policy applied to older requirement')
        if not snapshot.get('explicit_policy'):
            for line in lines:
                candidates=[pol for pol in policies.values() if pol['effective_date']<=line['created_at'][:10]]
                check(candidates and max(x['effective_date'] for x in candidates)==policy['effective_date'],'Calendar policy boundary crossed inside a group')
        for line in lines:
            members.append(identity(line))
            check(line['plant']==anchor['plant'],'Requirement mixes plants')
            check(0<=(datetime.fromisoformat(line['created_at']).date()-anchor_time.date()).days<=p['group_days'],'Grouping creation-date window violated')
            check(abs((date.fromisoformat(line['need_by_date'])-date.fromisoformat(anchor['need_by_date'])).days)<=p['need_days'],'Grouping need-by window violated')
            if line['item_code']:check(line['item_code'].casefold()==requirement['item_code'].casefold(),'Requirement mixes explicit catalog items')
        if requirement['item_code']=='NEW':check(len(lines)==1,'New items were grouped')
        quantity=sum((Decimal(line['quantity']) for line in lines),Decimal(0));valuation=e['valuation']
        check(quantity==Decimal(requirement['quantity'])==Decimal(valuation['quantity']),'Requirement quantity sum mismatch')
        exact=quantity*Decimal(valuation['unit_price'])
        check(exact==Decimal(valuation['exact_value']) and cents(exact)==requirement['group_value_inr'],'Independent financial valuation mismatch')
        check(all(row['group_value_inr']==cents(exact) for row in snapshot['rows'] if row['group_id']==rid),'CSV group valuation mismatch')
        if master:
            item=requirement['item_code'];ref=valuation['reference'];source=valuation['source'];price=Decimal(valuation['unit_price'])
            if source=='item_standard':check(price==Decimal(master['items'][item]['standard_price']),'Wrong item-standard valuation')
            elif source=='requester_estimate':check(price==Decimal(anchor['estimated_unit_price']),'Wrong requester-estimate valuation')
            elif source=='historical_po':
                history=sorted([h for h in master['history'] if h['item_code']==item and 0<(date.fromisoformat(asof)-date.fromisoformat(h['po_date'])).days<=p['history_days']],key=lambda h:(h['po_date'],h['po_number'],h['supplier_id']),reverse=True)
                check(bool(history) and history[0]['po_number']==ref and Decimal(history[0]['unit_price'])==price,'Wrong historical valuation reference')
            elif source=='contract':
                contracts=[c for c in master['contracts'] if c['contract_id']==ref and c['start_date']<=asof<=c['end_date']]
                check(any(Decimal(l['rate'])==price for c in contracts for l in c['lines'] if l['item_code']==item),'Wrong contract valuation reference')
            ranked=ranking(master,item,asof,policy) if item!='NEW' else []
            check([r['supplier_id'] for r in e['ranking']]==[r[0] for r in ranked],'Supplier ranking order mismatch')
            if requirement['route'] in {'RFQ','RFP','CAPEX_SOURCING'}:
                ranked_ids=[r[0] for r in ranked]
                category=master['items'][item]['category']
                extra=sorted([(sid,s) for sid,s in master['suppliers'].items() if s['status']=='Active' and sid not in p.get('excluded_supplier_ids',[]) and sid not in ranked_ids and category in s['categories'].split(';')],key=lambda pair:(-(Decimal(pair[1]['on_time_pct'])/100+Decimal(pair[1]['quality_rating'])/5),-Decimal(pair[1]['on_time_pct']),pair[0]))
                suggestions=(ranked_ids+[sid for sid,_ in extra])[:p['suggestions'].get(requirement['route'],3)]
                check(requirement['suggested_supplier_ids']==';'.join(suggestions),'Suggested suppliers violate rank/fallback order or requested count')
            sid=requirement['supplier_id']
            if sid:
                check(master['suppliers'].get(sid,{}).get('status')=='Active' and sid not in p.get('excluded_supplier_ids',[]),'Selected supplier is ineligible')
                if requirement['route'] in {'SPOT_PO','EMERGENCY_PO'}:check(ranked and sid==ranked[0][0] and Decimal(requirement['unit_price'])==ranked[0][2],'Wrong order supplier/reference price')
            if requirement['route']=='CONTRACT_PO':
                cid=e['selected_contract'];contract=next(c for c in master['contracts'] if c['contract_id']==cid)
                rate=next(Decimal(l['rate']) for l in contract['lines'] if l['item_code']==item)
                check(sid==contract['supplier_id'] and rate==Decimal(requirement['unit_price']),'Wrong contract order supplier/rate')
                allocated[cid]+=quantity*rate
                check(allocated[cid]<=Decimal(contract['value_cap'])-Decimal(contract['consumed_value']),'Contract ceiling exceeded')
    expected_members=[identity(r) for r in snapshot['rows'] if r['group_id']]
    check(Counter(members)==Counter(expected_members),'Missing/duplicated requirement memberships')
    for order in snapshot['orders']:
        for rid in order['requirements']:
            requirement=groups[rid];p=policies[requirement['policy_version']]['parameters']
            check((order['supplier_id'],order['plant'],order['route'])==(requirement['supplier_id'],requirement['plant'],requirement['route']),'PO consolidation mixes supplier/plant/route')
            check(0<=(datetime.fromisoformat(requirement['created_at'])-datetime.fromisoformat(order['anchor'])).total_seconds()<=p['po_hours']*3600,'PO consolidation time window violated')
    check(Counter(rid for order in snapshot['orders'] for rid in order['requirements'])==Counter(rid for rid,r in groups.items() if r['decision']=='PO'),'PO memberships are missing or duplicated')
    return {'input_hash':expected_hash,'requirements_checked':len(groups),'master_records_checked':master is not None}

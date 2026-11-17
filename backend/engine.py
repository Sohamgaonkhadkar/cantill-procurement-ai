"""Deterministic pipeline. Accepts snapshots; never mutates a database."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from collections import Counter
from .domain import D, Line, Requirement, digest, number, money, rate_text, OUTPUT_COLUMNS
from .matching import resolve
from .policy import validate_policy,evaluate
from .suppliers import history_for,preferred,suggestions,eligible

def validate_lines(rows,data):
    counts=Counter((r['pr_no'],r['pr_line']) for r in rows)
    result=[]
    for i,r in enumerate(rows):
        line=Line(r,i)
        try:
            line.created=datetime.fromisoformat(r['created_at'])
            if line.created.tzinfo is not None: raise ValueError('Use local Asia/Kolkata timestamps without offset')
            line.need=date.fromisoformat(r['need_by_date'])
            line.qty=number(r['quantity'])
            if line.qty<=0: line.errors.append('Quantity must be positive')
            if int(r['pr_line'])<=0: line.errors.append('PR line must be positive')
            if not r['pr_no']: line.errors.append('PR number required')
        except (ValueError,InvalidOperation,KeyError): line.errors.append('Invalid date, quantity or PR line')
        if r['plant'] not in data.plants: line.errors.append('Unknown plant: '+r['plant'])
        if r['urgency'] not in {'Normal','Emergency'}: line.errors.append('Urgency must be Normal or Emergency')
        if counts[(r['pr_no'],r['pr_line'])]>1: line.errors.append('Duplicate PR line identity in batch')
        line.item_code,line.match=resolve(r['item_code'],r['description'],r['uom'],data.items)
        if line.match.get('error'): line.errors.append(line.match['error'])
        line.item=data.items.get(line.item_code,{'item_code':'NEW','item_type':'New','category':'','description':r['description']})
        if line.item_code!='NEW' and r['uom'].upper()!=line.item['uom'].upper(): line.errors.append('UoM differs from item master')
        if line.item_code=='NEW':
            try:
                if number(r['estimated_unit_price'])<=0: raise ValueError()
            except (ValueError,InvalidOperation): line.errors.append('New item needs a positive estimated unit price')
        result.append(line)
    return result

def select_policy(policies,when,explicit=None):
    candidates=[p for p in policies if (p.get('status','active')=='active' or (explicit and p.get('status')=='superseded')) and p['effective_date']<=when.isoformat() and (not explicit or p['version']==explicit)]
    if not candidates: raise ValueError(f'No approved effective policy on {when}'+(f' for version {explicit}' if explicit else ''))
    effective=max(p['effective_date'] for p in candidates)
    latest=[p for p in candidates if p['effective_date']==effective]
    if len(latest)!=1: raise ValueError('Conflicting effective policies on '+effective+'; authorize an explicit supersession before processing')
    return latest[0]

def group_lines(lines,policies,explicit=None):
    groups=[]; invalid=[]; buckets={}
    for line in sorted(lines,key=lambda x:(x.created or datetime.max,x.raw['pr_no'],int(x.raw['pr_line']) if x.raw['pr_line'].isdigit() else 0,x.index)):
        if line.errors: invalid.append(line); continue
        try: policy=select_policy(policies,line.created.date(),explicit)
        except ValueError as e: line.errors.append(str(e)); invalid.append(line); continue
        match=None
        key=(line.item_code,line.raw['plant'],policy['version'])
        if line.item_code!='NEW':
            for g in buckets.get(key,[]):
                a=g.anchor; p=g.policy['parameters']
                if a.item_code==line.item_code and a.raw['plant']==line.raw['plant'] and g.policy['version']==policy['version'] and 0<=(line.created.date()-a.created.date()).days<=p['group_days'] and abs((line.need-a.need).days)<=p['need_days']:
                    match=g; break
        if match: match.lines.append(line)
        else:
            group=Requirement('REQ-'+digest([line.raw['pr_no'],line.raw['pr_line']])[:12].upper(),[line],policy)
            groups.append(group);buckets.setdefault(key,[]).append(group)
    return groups,invalid

def contract_candidates(data,g,allocated):
    candidates=[]
    for c in data.contracts:
        for l in c['lines']:
            if l['item_code']!=g.anchor.item_code: continue
            reason=None
            if not eligible(data,c['supplier_id'],g.policy): reason='Supplier not Active or excluded by policy'
            elif c['supplier_id'] in g.policy['parameters'].get('contract_excluded_supplier_ids',[]): reason='Contract supplier excluded by policy'
            elif not c['start_date']<=g.date.isoformat()<=c['end_date']: reason='Outside inclusive validity'
            rate=number(l['rate']); remaining=number(c['value_cap'])-number(c['consumed_value'])-allocated.get(c['contract_id'],D(0))
            applicable=reason is None
            if not reason and g.quantity*rate>remaining: reason='Insufficient remaining ceiling'
            candidates.append({'contract_id':c['contract_id'],'supplier_id':c['supplier_id'],'rate':str(rate),'remaining':str(remaining),'required':str(g.quantity*rate),'applicable':applicable,'usable':reason is None,'rejection':reason})
    return sorted(candidates,key=lambda c:(number(c['rate']),c['contract_id'],c['supplier_id']))

def decide(data,g,allocated):
    a=g.anchor; p=g.policy; params=p['parameters']; item=a.item_code
    candidates=contract_candidates(data,g,allocated)
    usable=next((c for c in candidates if c['usable']),None)
    applicable=next((c for c in candidates if c['applicable']),None)
    # Valuation history includes all recorded suppliers: a blocked supplier cannot
    # receive an order, but its historical invoice remains price evidence (3.1).
    valuation_history=history_for(data,item,g.date,params['history_days'],False)
    qualifying=history_for(data,item,g.date,params['history_days'],policy=p)
    if item=='NEW': rate=number(a.raw['estimated_unit_price']); source='requester_estimate'; reference=a.raw['pr_no']
    elif usable or applicable:
        chosen=usable or applicable; rate=number(chosen['rate']); source='contract'; reference=chosen['contract_id']
    elif valuation_history:
        rate=number(valuation_history[0]['unit_price']); source='historical_po'; reference=valuation_history[0]['po_number']
    else: rate=number(a.item['standard_price']); source='item_standard'; reference=item
    value=g.quantity*rate
    facts={'item.item_code':item,'item.item_type':a.item['item_type'],'item.category':a.item['category'],
        'requirement.plant':a.raw['plant'],'requirement.group_value_inr':str(value),'requirement.total_quantity':str(g.quantity),
        'requirement.is_emergency':any(l.raw['urgency']=='Emergency' for l in g.lines),'requirement.date':g.date.isoformat(),
        'contract.has_usable_contract':bool(usable),'contract.selected_supplier_id':usable['supplier_id'] if usable else None,
        'history.has_active_purchase_365d':bool(qualifying),'history.purchase_count':len(qualifying)}
    rule,trace=evaluate(p,facts); route=rule['route']; sid=''; unit=None; suggested=[]; relied=reference
    ranking=preferred(data,item,g.date,p) if item!='NEW' else []
    is_po=route in {'CONTRACT_PO','SPOT_PO','EMERGENCY_PO'}
    if route=='CONTRACT_PO':
        if usable:
            sid=usable['supplier_id']; unit=number(usable['rate']); relied=usable['contract_id']
            allocated[relied]=allocated.get(relied,D(0))+g.quantity*unit
        else: route='NOT_PROCESSED'; is_po=False
    elif route in {'SPOT_PO','EMERGENCY_PO'}:
        if ranking: sid=ranking[0]['supplier_id']; unit=number(ranking[0]['reference_price']); relied=ranking[0]['reference_source']
        else: route='NOT_PROCESSED'; is_po=False
    elif route not in {'NEW_ITEM_SOURCING','NOT_PROCESSED'} and item!='NEW':
        suggested=suggestions(data,a.item,ranking,params['suggestions'].get(route,3),p)
    reason=f"Policy {p['version']} clause {rule['id']}: {rule['reason']}. Valuation {source} {reference}."
    if is_po: reason+=f' Order price evidence {relied}.'
    if route in params['suggestions'] and len(suggested)<params['suggestions'][route]: reason+=f' Only {len(suggested)} eligible suppliers available.'
    if route=='NOT_PROCESSED': reason+=' No safe executable outcome; buyer review required.'
    evidence={'facts':facts,'rule_trace':trace,'valuation':{'unit_price':str(rate),'source':source,'reference':reference,'quantity':str(g.quantity),'exact_value':str(value),'lookback_days':params['history_days']},'contracts':candidates,'ranking':ranking,'order_reference':relied,'selected_contract':usable['contract_id'] if route=='CONTRACT_PO' else None,'group_anchor':a.raw,'grouping':'Fixed first-line anchor; inclusive calendar-day and need-by windows','matching':[l.match for l in g.lines]}
    approvals=1+(params.get('additional_sourcing_approvals',{}).get(a.item['item_type'],0) if not is_po and route!='NOT_PROCESSED' else 0)
    return {'id':g.id,'item_code':item,'description':a.item['description'],'plant':a.raw['plant'],'created_at':a.created.isoformat(),'need_by_date':a.need.isoformat(),'quantity':str(g.quantity),'decision':'PO' if is_po else 'SOURCING_REQUEST' if route!='NOT_PROCESSED' else '', 'route':route,'supplier_id':sid,'unit_price':rate_text(unit),'group_value_inr':money(value),'suggested_supplier_ids':';'.join(suggested),'policy_version':p['version'],'reason':reason,'po_id':'','evidence':evidence,'lines':[l.raw for l in g.lines],'approval_status':'pending','required_approvals':approvals}

def consolidate(decisions,groups):
    orders=[]; gm={g.id:g for g in groups}
    for d in decisions:
        if d['decision']!='PO': continue
        group=gm[d['id']]; hours=group.policy['parameters']['po_hours']; created=group.anchor.created
        order=next((o for o in orders if (o['supplier_id'],o['plant'],o['route'])==(d['supplier_id'],d['plant'],d['route']) and 0<=(created-o['anchor']).total_seconds()<=hours*3600),None)
        if not order:
            order={'id':'PO-'+digest([d['id'],d['supplier_id'],d['plant'],d['route']])[:12].upper(),'supplier_id':d['supplier_id'],'plant':d['plant'],'route':d['route'],'anchor':created,'requirements':[]}; orders.append(order)
        order['requirements'].append(d['id']); d['po_id']=order['id']; d['evidence']['po_anchor']=order['anchor'].isoformat()
    return [{**o,'anchor':o['anchor'].isoformat()} for o in orders]

def process(rows,data,policies,explicit=None):
    for p in policies: validate_policy(p)
    lines=validate_lines(rows,data); groups,invalid=group_lines(lines,policies,explicit)
    allocated={}; decisions=[decide(data,g,allocated) for g in groups]; orders=consolidate(decisions,groups)
    by_line={}
    for g,d in zip(groups,decisions):
        for line in g.lines:
            by_line[line.index]={**{k:d.get(k,'') for k in OUTPUT_COLUMNS},'pr_no':line.raw['pr_no'],'pr_line':line.raw['pr_line'],'resolved_item_code':line.item_code,'group_id':g.id}
    for line in invalid:
        version=explicit or ''
        if line.created:
            try: version=select_policy(policies,line.created.date(),explicit)['version']
            except ValueError: pass
        by_line[line.index]={**dict.fromkeys(OUTPUT_COLUMNS,''),'pr_no':line.raw['pr_no'],'pr_line':line.raw['pr_line'],'resolved_item_code':line.item_code,'route':'NOT_PROCESSED','reason':'; '.join(line.errors),'policy_version':version}
    # CSV ordering is independent of input row order for valid unique identities.
    output=sorted(by_line.values(),key=lambda r:(r['pr_no'],int(r['pr_line']) if r['pr_line'].isdigit() else 0,r['reason']))
    return {'rows':output,'requirements':decisions,'orders':orders,'allocations':{k:str(v) for k,v in allocated.items()},'issues':[{'pr_no':l.raw['pr_no'],'pr_line':l.raw['pr_line'],'errors':l.errors} for l in invalid],'output_hash':digest(output),'counts':dict(Counter(r['route'] for r in output))}

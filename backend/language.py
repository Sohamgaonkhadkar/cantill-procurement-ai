"""Conservative English-to-policy compiler for explicit procurement statements.

Only supported complete statements compile. Unknown text remains visible and
blocks ordinary review until a human explicitly verifies manual interpretation.
"""
from copy import deepcopy
import re
from .domain import number,digest
from .policy import condition,validate_policy

AMOUNT=r'(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)\s*(lakhs?|lacs?|crores?|million)?'
ROUTE=r'(CONTRACT_PO|EMERGENCY_PO|SPOT_PO|RFQ|RFP|CAPEX_SOURCING|NEW_ITEM_SOURCING)'

def amount(value,unit=None):
    return str(number(value)*{'lakh':100000,'lac':100000,'crore':10000000,'million':1000000}.get((unit or '').lower().rstrip('s'),1))

def leaves(node):
    if 'fact' in node: yield node
    for key in ['all','any']:
        for child in node.get(key,[]): yield from leaves(child)
    if 'not' in node: yield from leaves(node['not'])

def canonical(value,choices):
    value=value.strip().strip('"\'')
    exact=[x for x in choices if x.casefold()==value.casefold()]
    if len(exact)==1: return exact[0]
    words={w.rstrip('s') for w in re.findall(r'\w+',value.casefold())}
    partial=[x for x in choices if words and words<={w.rstrip('s') for w in re.findall(r'\w+',x.casefold())}]
    if len(partial)==1: return partial[0]
    raise ValueError('Unknown or ambiguous scope value: '+value)

def predicate(text,data=None):
    text=re.sub(r'^the\s+','',text.strip(),flags=re.I)
    m=re.fullmatch(r'plant\s*(?:is|equals|=|:)?\s+(.+)',text,re.I)
    if m:
        value=m[1].strip().strip('"\'')
        if data:
            plant_values={p:p for p in data.plants}
            for key,p in data.plants.items(): plant_values[p['name']]=key
            value=plant_values[canonical(value,plant_values)]
        return condition('requirement.plant','eq',value)
    m=re.fullmatch(r'(?:item\s+)?category\s*(?:is|equals|=|:)?\s+(.+)',text,re.I)
    if m:
        value=m[1].strip().strip('"\'')
        if data: value=canonical(value,{x['category'] for x in data.items.values()})
        return condition('item.category','eq',value)
    m=re.fullmatch(r'(?:item\s+)?type\s*(?:is|equals|=|:)?\s+(Material|Service|Capex)',text,re.I)
    if m: return condition('item.item_type','eq',m[1].capitalize())
    m=re.fullmatch(r'item\s+code\s*(?:is|equals|=|:)?\s+([\w-]+)',text,re.I)
    if m:
        value=m[1]
        if data: value=canonical(value,data.items)
        return condition('item.item_code','eq',value)
    if re.fullmatch(r'(?:urgency\s+is\s+)?emergency',text,re.I): return condition('requirement.is_emergency','eq',True)
    if re.fullmatch(r'(?:urgency\s+is\s+)?normal',text,re.I): return condition('requirement.is_emergency','eq',False)
    m=re.fullmatch(r'(?:requirement\s+|group\s+)?(?:value|amount)\s+(exceeds|above|greater than|more than|at least|at or above|>=|less than|below|under|at most|at or below|<=|>|<|equals|=)\s*'+AMOUNT,text,re.I)
    if m:
        operator={'exceeds':'gt','above':'gt','greater than':'gt','more than':'gt','>':'gt','at least':'gte','at or above':'gte','>=':'gte','less than':'lt','below':'lt','under':'lt','<':'lt','at most':'lte','at or below':'lte','<=':'lte','equals':'eq','=':'eq'}[m[1].lower()]
        return condition('requirement.group_value_inr',operator,amount(m[2],m[3]))
    m=re.fullmatch(r'(?:requirement\s+)?date\s+(on or after|on or before|after|before|is)\s+(\d{4}-\d{2}-\d{2})',text,re.I)
    if m: return condition('requirement.date',{'on or after':'gte','on or before':'lte','after':'gt','before':'lt','is':'eq'}[m[1].lower()],m[2])
    raise ValueError('Unsupported or incomplete condition: '+text)

def conditions(text,data=None):
    # Quoted values protect category names containing “and” or “or”.
    parts=re.split(r'("[^"]*"|\'[^\']*\')',text)
    placeholders={}
    for i in range(1,len(parts),2): placeholders[f'__quoted_{i}__']=parts[i]; parts[i]=f'__quoted_{i}__'
    text=''.join(parts)
    text=re.sub(r'\d[\d,]*(?:\.\d+)?',lambda m:str(number(m[0])) if ',' in m[0] else m[0],text)
    text=re.sub(r',\s*(?:and\s+)?',' and ',text,flags=re.I)
    groups=[]
    for alternative in re.split(r'\s+or\s+(?!after\b|before\b|above\b|below\b)',text,flags=re.I):
        terms=[]
        for term in re.split(r'\s+and\s+',alternative,flags=re.I):
            for key,value in placeholders.items(): term=term.replace(key,value)
            negated=term.strip().lower().startswith('not ')
            node=predicate(term.strip()[4:] if negated else term,data)
            terms.append({'not':node} if negated else node)
        groups.append(terms[0] if len(terms)==1 else {'all':terms})
    return groups[0] if len(groups)==1 else {'any':groups}

COUNT=r'(?:[0-9]+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)'

def count(value):
    words=['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen','twenty']
    return int(value) if value.isdigit() else words.index(value.lower())

def supplier_id(value,data):
    if data is None: raise ValueError('Supplier restrictions require master-data validation')
    choices={sid:sid for sid in data.suppliers}
    for sid,supplier in data.suppliers.items():
        name=supplier['name']
        if name in choices and choices[name]!=sid:raise ValueError('Ambiguous supplier name; use its ID')
        choices[name]=sid
    return choices[canonical(value,choices)]

def parse_date(value):
    from datetime import date
    value=value.strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return date.fromisoformat(value).isoformat()
    match=re.fullmatch(r'(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})',value,re.I)
    if not match:raise ValueError('Use an explicit ISO date or day month year')
    months=['january','february','march','april','may','june','july','august','september','october','november','december']
    return date(int(match[3]),months.index(match[2].lower())+1,int(match[1])).isoformat()

def apply_statement(policy,text,data=None,context=None):
    text=text.strip().rstrip('.').strip()
    prefix=r'(?:(?:please|change|set|update|revise|increase|decrease|reduce|the|new)\s+)*'
    # Explicit preservation is recorded, never interpreted as a request to mutate.
    m=re.fullmatch(r"(?:do not|don't) change (?:the )?(spot|emergency|rfq|rfp)(?:[- ](?:purchase|purchasing|PO))? (?:limit|threshold)",text,re.I)
    if m:
        if context is not None: context.setdefault('preserved_labels',set()).add(m[1].lower())
        return 'Preserve '+m[1].lower()+' threshold without changing it'
    if re.fullmatch(r'exclude (?:inactive|blocked|inactive and blocked|blocked and inactive) suppliers from all (?:purchasing )?(?:recommendations|purchases)',text,re.I):
        return 'Preserve mandatory Active-only supplier eligibility'
    m=re.fullmatch(r'(?:exclude contracts from|do not use contracts from) (?:supplier )?(.+)',text,re.I)
    if m:
        sid=supplier_id(m[1],data);key='contract_excluded_supplier_ids'
        policy['parameters'][key]=sorted(set(policy['parameters'].get(key,[])+[sid]))
        return 'Exclude contracts and contract-only reference relationships from '+sid
    m=re.fullmatch(r'(?:exclude|do not recommend) supplier (.+?)(?: from all (?:purchasing )?(?:recommendations|purchases))?',text,re.I)
    if m:
        sid=supplier_id(m[1],data);key='excluded_supplier_ids'
        policy['parameters'][key]=sorted(set(policy['parameters'].get(key,[])+[sid]))
        return 'Exclude '+sid+' from purchasing eligibility and suggestions'
    m=re.fullmatch(prefix+r'(frequency|recency|contract|delivery|quality)(?: ranking)? weight (?:to|is|=|:)\s*([0-9]+(?:\.[0-9]+)?)%?',text,re.I)
    if m:
        policy['parameters']['weights'][m[1].lower()]=float(number(m[2]))
        return m[1].lower()+' ranking weight proposed: '+m[2]
    m=re.fullmatch(r'(?:increase|change|set) (?:the )?(?:preferred )?supplier count for '+ROUTE+r'(?: from '+COUNT+r')? to ('+COUNT+r')',text,re.I)
    if m:
        route=m[1].upper()
        if route not in {'RFQ','RFP','CAPEX_SOURCING'}: raise ValueError('Supplier counts apply to sourcing')
        policy['parameters']['suggestions'][route]=count(m[2])
        return route+' supplier count proposed: '+str(count(m[2]))
    m=re.fullmatch(r'for (capital equipment|capex|materials|services),? require (?:an |one )?additional sourcing approval',text,re.I)
    if m:
        kind={'capital equipment':'Capex','capex':'Capex','materials':'Material','services':'Service'}[m[1].lower()]
        policy['parameters'].setdefault('additional_sourcing_approvals',{})[kind]=1
        return kind+' sourcing requires two distinct approving identities'
    m=re.fullmatch(r'(?:apply|make) (?:the )?(policy|version|new rule|rule) (?:effective )?(?:only )?from (.+)',text,re.I)
    if m:
        effective=parse_date(m[2])
        if 'rule' in m[1].lower():
            ids=(context or {}).get('added_rule_ids',[])
            if len(ids)!=1: raise ValueError('Effective-date instruction must identify one new rule, or specify policy effective date')
            rule=next(r for r in policy['rules'] if r['id']==ids[0])
            rule['when']={'all':[rule['when'],condition('requirement.date','gte',effective)]}
            return 'New rule applies on or after '+effective
        policy['effective_date']=effective
        return 'Policy effective date proposed: '+effective
    m=re.fullmatch(r'at plant (.+?),? require '+ROUTE+r' for (.+?) purchases (above|below|at least|at most) '+AMOUNT+r'(?: (except|unless) (.+))?',text,re.I)
    if m:
        plant,route,category,operator,value,unit,exception,exclusion=m.groups()
        scope='plant '+plant.rstrip(',')+' and category '+category+' and value '+operator+' '+value+(' '+unit if unit else '')
        if exception:scope+=' except '+exclusion
        return apply_statement(policy,'If '+scope+' require '+route,data,context)
    m=re.fullmatch(prefix+r'(spot|emergency|rfq|rfp)(?:[- ](?:purchase|purchasing|PO))?\s+(?:limit|threshold)\s*(?:to|of|is|=|:)?\s*'+AMOUNT,text,re.I)
    if m:
        label=m[1].lower(); value=amount(m[2],m[3])
        routes={'spot':['SPOT_PO'],'emergency':['EMERGENCY_PO'],'rfq':['RFQ','RFP'],'rfp':['RFQ','RFP']}[label]
        changed=0
        for route in routes:
            rules=[r for r in policy['rules'] if r['route']==route and not any(x['fact'] in {'requirement.plant','item.category','item.item_type','item.item_code'} for x in leaves(r['when']))]
            if len(rules)!=1: raise ValueError('No unique global rule for '+route)
            for leaf in leaves(rules[0]['when']):
                if leaf['fact']=='requirement.group_value_inr': leaf['value']=value; changed+=1
        if not changed: raise ValueError('No amount predicate was found')
        return f'{label} global limit proposed: INR {value}'
    m=re.fullmatch(prefix+r'(grouping|clubbing|need.by|history|preferred.history|PO consolidation)\s+(?:window|period)\s+(?:to|is|=)?\s*('+COUNT+r')\s+(?:calendar\s+)?(days?|hours?)',text,re.I)
    if m:
        key={'grouping':'group_days','clubbing':'group_days','need-by':'need_days','need by':'need_days','history':'history_days','preferred history':'preferred_days','preferred-history':'preferred_days','po consolidation':'po_hours'}.get(m[1].lower())
        if not key or (key=='po_hours')!=m[3].lower().startswith('hour'): raise ValueError('Window unit does not match parameter')
        policy['parameters'][key]=count(m[2]); return f'{key} proposed: {m[2]}'
    m=re.fullmatch(r'(?:suggest|use)\s+(\d+)\s+suppliers?\s+for\s+'+ROUTE,text,re.I)
    if m:
        route=m[2].upper()
        if route not in {'RFQ','RFP','CAPEX_SOURCING'}: raise ValueError('Suggestion count applies to sourcing routes')
        policy['parameters']['suggestions'][route]=int(m[1]); return f'{route} supplier count proposed: {m[1]}'
    m=re.fullmatch(r'(?:if|when)\s+(.+?)[,;]?\s+(?:then\s+)?(?:require|use|route to|raise)\s+'+ROUTE+r'(?:\s*\(priority\s+(-?\d+)\))?',text,re.I)
    if m:
        scope=m[1].strip().rstrip(',;').strip()
        exception=re.split(r'\s+(?:unless|except(?:\s+when)?)\s+',scope,maxsplit=1,flags=re.I)
        node=conditions(exception[0],data)
        if len(exception)==2: node={'all':[node,{'not':conditions(exception[1],data)}]}
        route=m[2].upper()
        rid='amendment-'+digest([node,route])[:12]
        if any(r['id']==rid for r in policy['rules']): raise ValueError('Equivalent amendment rule already exists')
        priorities={r['priority'] for r in policy['rules']}
        priority=int(m[3]) if m[3] else next(i for i in range(1,10000) if i not in priorities)
        if priority in priorities: raise ValueError('Conflicting priority: requested priority is already used')
        policy['rules'].append({'id':rid,'priority':priority,'when':node,'route':route,'reason':'Reviewed amendment: '+text})
        return f'New {route} rule proposed at priority {priority}; review scope and precedence'
    raise ValueError('Statement needs structured manual authoring')

def limit_signature(policy,label):
    routes={'spot':{'SPOT_PO'},'emergency':{'EMERGENCY_PO'},'rfq':{'RFQ','RFP'},'rfp':{'RFQ','RFP'}}[label]
    return [(r['id'],[(x['op'],str(x['value'])) for x in leaves(r['when']) if x['fact']=='requirement.group_value_inr']) for r in policy['rules'] if r['route'] in routes and not any(x['fact'] in {'requirement.plant','item.category','item.item_type','item.item_code'} for x in leaves(r['when']))]


def interpret(base,text,version,effective_date,data=None):
    from .amendments import policy_diff
    policy=deepcopy(base); policy.pop('status',None); policy.pop('governance',None)
    policy.update(version=version,effective_date=effective_date)
    detected=[];unresolved=[];coverage=[];conflicts=[];updates={}
    context={'preserved_labels':set(),'added_rule_ids':[]}
    if len(text)>100000: raise ValueError('Policy text exceeds the 100,000-character interpretation limit')
    commands=r'if|when|change|set|update|revise|increase|decrease|reduce|suggest|use|do not|exclude|at plant|for |apply|make'
    lines=[re.sub(r'^\s*(?:[0-9]+[.)]|[-•])\s+','',x.strip()) for x in re.split(r'[\n;]+|(?<=[.!?])\s+(?=(?:'+commands+r')\b)',text,flags=re.I) if x.strip()]
    if len(lines)>500: raise ValueError('Policy has too many source lines for automatic interpretation')
    statements=[];buffer=''
    for line in lines:
        complete=False
        if buffer:
            try: apply_statement(deepcopy(policy),buffer,data,deepcopy(context));complete=True
            except ValueError: pass
        starts=bool(re.match(r'^(?:'+commands+r')\b',line,re.I))
        if buffer and (complete or starts):statements.append(buffer);buffer=line
        else:buffer=(buffer+' '+line).strip()
    if buffer:statements.append(buffer)
    for statement in statements:
        candidate=deepcopy(policy);candidate_context=deepcopy(context)
        try:
            description=apply_statement(candidate,statement,data,candidate_context)
            validate_policy(candidate)
            for label in candidate_context['preserved_labels']:
                if limit_signature(candidate,label)!=limit_signature(base,label):
                    raise ValueError('Conflicting instruction: preserve '+label+' threshold but another clause changes it')
            diffs=policy_diff(policy,candidate)
            for diff in diffs:
                previous=updates.get(diff['path'])
                if previous and previous['value']!=diff['after']:
                    raise ValueError('Conflicting amendments target '+diff['path'])
            added=[r for r in candidate['rules'] if r['id'] not in {x['id'] for x in policy['rules']}]
            for rule in added:
                for existing in policy['rules']:
                    if existing['id'] in context['added_rule_ids'] and digest(existing['when'])==digest(rule['when']) and existing['route']!=rule['route']:
                        raise ValueError('Conflicting new routes for the same condition: '+existing['route']+' and '+rule['route'])
            candidate_context['added_rule_ids'] += [r['id'] for r in added]
            for diff in diffs:updates[diff['path']]={'value':diff['after'],'source':statement}
            policy=candidate;context=candidate_context;detected.append(description)
            coverage.append({'text':statement,'status':'proposed' if diffs else 'preserved','description':description,'changed_paths':[x['path'] for x in diffs]})
        except ValueError as exc:
            entry={'text':statement,'reason':str(exc)};unresolved.append(entry)
            conflicting='conflict' in str(exc).lower()
            if conflicting:conflicts.append(entry)
            coverage.append({'text':statement,'status':'conflict' if conflicting else 'unresolved','reason':str(exc)})
    validate_policy(policy)
    return {'policy':policy,'detected_changes':detected,'unresolved_clauses':unresolved,'conflicts':conflicts,'source_clauses':coverage,'complete':not unresolved}

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
    words=set(re.findall(r'\w+',value.casefold()))
    partial=[x for x in choices if words and words<=set(re.findall(r'\w+',x.casefold()))]
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

def apply_statement(policy,text,data=None):
    text=text.strip().rstrip('.').strip()
    prefix=r'(?:(?:please|change|set|update|revise|increase|decrease|reduce|the|new)\s+)*'
    m=re.fullmatch(prefix+r'(spot|emergency|rfq|rfp)\s+(?:PO\s+)?(?:limit|threshold)\s*(?:to|of|is|=|:)?\s*'+AMOUNT,text,re.I)
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
    m=re.fullmatch(prefix+r'(grouping|clubbing|need.by|history|preferred.history|PO consolidation)\s+(?:window|period)\s+(?:to|is|=)?\s*(\d+)\s+(days?|hours?)',text,re.I)
    if m:
        key={'grouping':'group_days','clubbing':'group_days','need-by':'need_days','need by':'need_days','history':'history_days','preferred history':'preferred_days','preferred-history':'preferred_days','po consolidation':'po_hours'}.get(m[1].lower())
        if not key or (key=='po_hours')!=m[3].lower().startswith('hour'): raise ValueError('Window unit does not match parameter')
        policy['parameters'][key]=int(m[2]); return f'{key} proposed: {m[2]}'
    m=re.fullmatch(r'(?:suggest|use)\s+(\d+)\s+suppliers?\s+for\s+'+ROUTE,text,re.I)
    if m:
        route=m[2].upper()
        if route not in {'RFQ','RFP','CAPEX_SOURCING'}: raise ValueError('Suggestion count applies to sourcing routes')
        policy['parameters']['suggestions'][route]=int(m[1]); return f'{route} supplier count proposed: {m[1]}'
    m=re.fullmatch(r'(?:if|when)\s+(.+?)[,;]?\s+(?:then\s+)?(?:require|use|route to|raise)\s+'+ROUTE+r'(?:\s*\(priority\s+(-?\d+)\))?',text,re.I)
    if m:
        scope=m[1].strip().rstrip(',;').strip()
        if re.search(r'\b(?:unless|except)\b',scope,re.I): raise ValueError('Exception clauses require manual structured authoring')
        node=conditions(scope,data); route=m[2].upper()
        rid='amendment-'+digest([node,route])[:12]
        if any(r['id']==rid for r in policy['rules']): raise ValueError('Equivalent amendment rule already exists')
        priorities={r['priority'] for r in policy['rules']}
        priority=int(m[3]) if m[3] else next(i for i in range(1,10000) if i not in priorities)
        if priority in priorities: raise ValueError('Requested priority is already used')
        policy['rules'].append({'id':rid,'priority':priority,'when':node,'route':route,'reason':'Reviewed amendment: '+text})
        return f'New {route} rule proposed at priority {priority}; review scope and precedence'
    raise ValueError('Statement needs structured manual authoring')

def interpret(base,text,version,effective_date,data=None):
    policy=deepcopy(base); policy.pop('status',None); policy.pop('governance',None)
    policy.update(version=version,effective_date=effective_date)
    detected=[]; unresolved=[]
    # Each nonempty line/semicolon statement must be accounted for. Decimal
    # points are not sentence separators, and no prose is silently discarded.
    if len(text)>100000: raise ValueError('Policy text exceeds the 100,000-character interpretation limit')
    lines=[x.strip() for x in re.split(r'[\n;]+',text) if x.strip()]
    if len(lines)>500: raise ValueError('Policy has too many source lines for automatic interpretation')
    statements=[]; buffer=''
    for line in lines:
        complete=False
        if buffer:
            try: apply_statement(deepcopy(policy),buffer,data); complete=True
            except ValueError: pass
        starts_statement=bool(re.match(r'^(?:if|when|change|set|update|revise|increase|decrease|reduce|suggest|use)\b',line,re.I))
        if buffer and (complete or starts_statement): statements.append(buffer); buffer=line
        else: buffer=(buffer+' '+line).strip()
    if buffer: statements.append(buffer)
    for statement in statements:
        candidate=deepcopy(policy)
        try:
            description=apply_statement(candidate,statement,data)
            validate_policy(candidate)
            policy=candidate; detected.append(description)
        except ValueError as exc: unresolved.append({'text':statement,'reason':str(exc)})
    validate_policy(policy)
    return {'policy':policy,'detected_changes':detected,'unresolved_clauses':unresolved,'complete':not unresolved}

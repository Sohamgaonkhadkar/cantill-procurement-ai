"""Clause-by-clause human review evidence tied to actual executable edits."""
import re
from .domain import digest,number
from .amendments import field_diff
from .language import leaves,AMOUNT,amount

def clause_id(entry,index):return entry.get('id') or 'CLAUSE-'+digest([index,entry['text']])[:16]

def resolve(document,path):
    value=document
    for token in re.findall(r'[^.\[\]]+|\[[^\]]+\]',path):
        if token.startswith('['):
            key=token[1:-1]
            if isinstance(value,list) and any(isinstance(v,dict) and v.get('id')==key for v in value):value=next(v for v in value if isinstance(v,dict) and v.get('id')==key)
            else:value=value[int(key)]
        else:value=value[token]
    return value

def intersects(left,right):
    return left==right or any(left.startswith(right+s) or right.startswith(left+s) for s in ['.','['])

def parameter_supported(path,text):
    hints={'group_days':['group','club'],'need_days':['need-by','need by'],'history_days':['history'],'preferred_days':['preferred'],'po_hours':['consolidat'],'preferred_count':['preferred'],'recency_days':['recency'],'frequency_cap':['frequency'],'additional_sourcing_approvals':['approval'],'excluded_supplier_ids':['exclude','do not recommend'],'contract_excluded_supplier_ids':['contract']}
    key=path.split('.')[1]
    if key=='weights':return len(path.split('.'))>=3 and path.split('.')[2] in text and ('weight' in text or 'ranking' in text)
    if key=='suggestions':return 'supplier' in text and any(route.lower() in text for route in ['RFQ','RFP','CAPEX_SOURCING'])
    return any(word in text for word in hints.get(key,[]))

def source_checks(text,rules,data):
    """Check recognizable source facts; unknown semantics still require a human."""
    from .precedence import witness as symbolic_witness,AnalysisBound
    def witness(left,right):
        try:return symbolic_witness(left,right)
        except AnalysisBound:raise ValueError('Reconciliation analysis exceeds its safety bound; simplify the mapped conditions and review their scope explicitly') from None
    lower=text.casefold();nodes=[leaf for rule in rules for leaf in leaves(rule['when'])]
    mentioned_plants=[];mentioned_categories=[]
    for pid,plant in data.plants.items():
        names=[pid,*[w for w in re.findall(r'\w+',plant['name']) if len(w)>4 and w.lower()!='plant']]
        if any(re.search(r'(?<![\w-])'+re.escape(n)+r'(?![\w-])',text,re.I) for n in names):
            mentioned_plants.append(pid)
            if not any(n['fact']=='requirement.plant' and (n.get('value')==pid or isinstance(n.get('value'),list) and pid in n['value']) for n in nodes):raise ValueError('Mapped rule is missing the source plant '+pid)
    for category in {i['category'] for i in data.items.values()}:
        if re.search(r'\b'+re.escape(category.rstrip('s'))+r's?\b',text,re.I):
            mentioned_categories.append(category)
            if not any(n['fact']=='item.category' and (n.get('value')==category or isinstance(n.get('value'),list) and category in n['value']) for n in nodes):raise ValueError('Mapped rule is missing the source category '+category)
    routes=set(re.findall(r'\b(?:RFQ|RFP|SPOT_PO|EMERGENCY_PO|CONTRACT_PO|CAPEX_SOURCING|NEW_ITEM_SOURCING)\b',text,re.I))
    if routes and not {r.upper() for r in routes}<={r['route'] for r in rules}:raise ValueError('Mapped rule does not implement the source route')
    values=[]
    for m in re.finditer(r'(?:INR|₹|Rs\.?)\s*([\d,]+(?:\.\d+)?)\s*(lakhs?|lacs?|crores?|million)?',text,re.I):values.append(number(amount(m[1],m[2])))
    between=re.search(r'between\s+'+AMOUNT+r'\s+and\s+'+AMOUNT,text,re.I)
    if between:values.extend([number(amount(between[1],between[2])),number(amount(between[3],between[4]))])
    monetary=[number(n['value']) for n in nodes if n['fact']=='requirement.group_value_inr' and not isinstance(n.get('value'),list) and n.get('value') is not None]
    if values and not all(v in monetary for v in values):raise ValueError('Mapped value predicates do not contain the stated source amounts')
    # Merely mentioning the right literal inside NOT/ANY does not constrain a
    # rule to the source scope. Prove the recognizable positive single scope.
    if not re.search(r'\b(?:except|not|other than)\s+(?:the\s+)?(?:plant|category)\b',lower):
        for fact,values in [('requirement.plant',mentioned_plants),('item.category',mentioned_categories)]:
            if len(values)==1:
                outside={'fact':fact,'op':'ne','value':values[0]}
                if any(witness(rule['when'],outside) is not False for rule in rules):raise ValueError('Mapped rule permits requests outside the stated source scope')
    if between and re.search(r'\binclusive\b',text,re.I):
        low=amount(between[1],between[2]);high=amount(between[3],between[4])
        for rule in rules:
            for bound in [low,high]:
                if witness(rule['when'],{'fact':'requirement.group_value_inr','op':'eq','value':bound}) is False:raise ValueError('Mapped rule does not include both stated inclusive boundaries')
            for op,bound in [('lt',low),('gt',high)]:
                if witness(rule['when'],{'fact':'requirement.group_value_inr','op':op,'value':bound}) is not False:raise ValueError('Mapped rule exceeds the stated inclusive interval')
    if re.search(r'\bnormal\b',lower) and (not re.search(r'\bemergency\b',lower) or re.search(r'\bnormal\s+requests?\b',lower)):
        # Either eq False, ne True or NOT(eq True) is a valid normal predicate.
        emergency={'fact':'requirement.is_emergency','op':'eq','value':True}
        if any(witness(rule['when'],emergency) is not False for rule in rules):raise ValueError('A normal-only source clause still permits emergency requests')

def verify(policy,governance,mappings,data):
    unresolved=governance.get('interpretation',{}).get('unresolved_clauses',[])
    original=governance.get('interpretation_definition')
    if not original:
        if unresolved:raise ValueError('Re-upload this legacy unresolved draft to capture its original structured definition before reconciliation')
        return []
    changed=field_diff(original,{k:policy[k] for k in ['version','effective_date','parameters','rules']})
    paths=[d['path'] for d in changed if d['path']!='version']
    expected={clause_id(entry,index):entry for index,entry in enumerate(unresolved)}
    provided={m.clause_id:m for m in mappings}
    if len(provided)!=len(mappings) or set(provided)!=set(expected):raise ValueError('Provide exactly one confirmed reconciliation for every unresolved clause')
    evidence=[]
    for cid,entry in expected.items():
        mapping=provided[cid]
        if not mapping.confirmed:raise ValueError('Confirm each source-clause mapping explicitly')
        rules=[];targets=[]
        for path in mapping.paths:
            if not re.fullmatch(r'(?:rules\[[^\]]+\](?:\.[\w.\[\]-]+)?|parameters\.[\w.\[\]-]+|effective_date)',path):raise ValueError('Map a concrete executable rule, parameter or effective-date path')
            if not any(intersects(path,p) for p in paths):raise ValueError('Mapped path has no saved change from the interpreted draft: '+path)
            try:value=resolve(policy,path)
            except (KeyError,TypeError,ValueError,IndexError):raise ValueError('Mapped policy path does not exist: '+path) from None
            if path.startswith('rules['):
                root=re.match(r'rules\[[^\]]+\]',path)[0];rule=resolve(policy,root)
                try:prior=resolve(original,root)
                except (KeyError,TypeError,ValueError,IndexError):prior=None
                if prior and all(prior[k]==rule[k] for k in ['when','priority','route']):raise ValueError('A reason-only edit cannot reconcile an executable clause')
                rules.append(rule)
            elif path.startswith('parameters.') and not parameter_supported(path,entry['text'].casefold()):raise ValueError('Parameter path is unrelated to the recognizable source instruction')
            elif path=='effective_date' and not re.search(r'\b(?:effective|from|date)\b',entry['text'],re.I):raise ValueError('Date-only edit does not implement this clause')
            if path=='effective_date':
                stated_dates=re.findall(r'\b\d{4}-\d{2}-\d{2}\b',entry['text'])
                if stated_dates and value not in stated_dates:raise ValueError('Saved effective date differs from the stated source date')
            targets.append({'path':path,'value':value})
        if rules:source_checks(entry['text'],rules,data)
        allowed_dates={policy['effective_date'],*[str(n.get('value')) for r in rules for n in leaves(r['when']) if n['fact']=='requirement.date']}
        if mapping.effective_date.isoformat() not in allowed_dates:raise ValueError('Reconciliation effective date does not match the saved policy or rule')
        priorities=sorted({r['priority'] for r in rules})
        if mapping.priority is not None and mapping.priority not in priorities:raise ValueError('Reconciliation priority does not match a mapped rule')
        evidence.append({'clause_id':cid,'original_text':entry['text'],**mapping.model_dump(mode='json'),'targets':targets,'actual_priorities':priorities,'definition_hash':digest({k:policy[k] for k in ['version','effective_date','parameters','rules']}),'source_hash':governance.get('source_hash'),'changed_paths':[p for p in paths if any(intersects(p,x) for x in mapping.paths)]})
    return evidence

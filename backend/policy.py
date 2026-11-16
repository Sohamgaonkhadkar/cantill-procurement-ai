"""Validated first-match policy language. No runtime code evaluation."""
from datetime import date
from decimal import Decimal
from copy import deepcopy
from .domain import number

FACTS = {
 'item.item_type':str,'item.category':str,'item.item_code':str,
 'requirement.plant':str,'requirement.group_value_inr':Decimal,
 'requirement.is_emergency':bool,'requirement.total_quantity':Decimal,
 'requirement.date':date,'contract.has_usable_contract':bool,
 'contract.selected_supplier_id':str,'history.has_active_purchase_365d':bool,
 'history.purchase_count':Decimal,
}
ROUTES = {'CAPEX_SOURCING','CONTRACT_PO','EMERGENCY_PO','SPOT_PO','RFQ','RFP','NEW_ITEM_SOURCING','NOT_PROCESSED'}
OPS = {'eq','ne','gt','gte','lt','lte','in','not_in','exists','is_null'}

def condition(fact, op, value): return {'fact':fact,'op':op,'value':value}

def initial_policy():
    c = condition
    return {
      'version':'5.0','effective_date':'2026-04-01',
      'parameters':{'group_days':14,'need_days':7,'history_days':365,'preferred_days':548,
        'po_hours':24,'preferred_count':3,'suggestions':{'RFQ':3,'RFP':5,'CAPEX_SOURCING':5},
        'weights':{'frequency':25,'recency':25,'contract':20,'delivery':15,'quality':15},
        'recency_days':[90,365],'frequency_cap':10},
      'rules':[
        {'id':'1.2','priority':0,'when':c('item.item_code','eq','NEW'),'route':'NEW_ITEM_SOURCING','reason':'New item; buyer must identify suppliers'},
        {'id':'5.1','priority':10,'when':c('item.item_type','eq','Capex'),'route':'CAPEX_SOURCING','reason':'Capital equipment requires sourcing and capex approval'},
        {'id':'5.2','priority':20,'when':c('contract.has_usable_contract','eq',True),'route':'CONTRACT_PO','reason':'Eligible contract with sufficient ceiling'},
        {'id':'5.3','priority':30,'when':{'all':[c('requirement.is_emergency','eq',True),c('requirement.group_value_inr','lte','500000'),c('history.has_active_purchase_365d','eq',True)]},'route':'EMERGENCY_PO','reason':'Emergency within limit with qualifying active-supplier history'},
        {'id':'5.4','priority':40,'when':{'all':[c('requirement.group_value_inr','lt','200000'),c('history.has_active_purchase_365d','eq',True)]},'route':'SPOT_PO','reason':'Below spot limit with qualifying active-supplier history'},
        {'id':'5.5','priority':50,'when':c('requirement.group_value_inr','lt','1000000'),'route':'RFQ','reason':'Request competitive quotations'},
        {'id':'5.6','priority':60,'when':c('requirement.group_value_inr','gte','1000000'),'route':'RFP','reason':'Formal sourcing at or above RFP threshold'},
      ]}

def coerce(fact, value):
    typ = FACTS[fact]
    if value is None: return None
    if typ is Decimal: return number(value)
    if typ is date: return date.fromisoformat(str(value))
    if typ is bool and not isinstance(value,bool): raise ValueError(f'{fact} expects a boolean')
    if typ is str and not isinstance(value,str): raise ValueError(f'{fact} expects text')
    return value

def validate_condition(node, depth=0):
    if depth>12 or not isinstance(node,dict): raise ValueError('Invalid/deep condition')
    logical = set(node) & {'all','any','not'}
    if logical:
        if len(node)!=1: raise ValueError('Boolean nodes must contain one operator')
        key = next(iter(logical)); children = [node[key]] if key=='not' else node[key]
        if not isinstance(children,list) or not children: raise ValueError('Boolean condition needs children')
        for child in children: validate_condition(child,depth+1)
        return
    if set(node)-{'fact','op','value'} or node.get('fact') not in FACTS or node.get('op') not in OPS:
        raise ValueError('Unknown fact, operator or condition field')
    if node['op'] in {'in','not_in'}:
        if not isinstance(node.get('value'),list): raise ValueError('Membership expects a list')
        for v in node['value']: coerce(node['fact'],v)
    elif node['op'] not in {'exists','is_null'}:
        if node.get('value') is None: raise ValueError('Comparison value required')
        coerce(node['fact'],node['value'])

def _validate_policy(policy):
    date.fromisoformat(policy['effective_date'])
    if not policy.get('version') or len(policy['version'])>60: raise ValueError('Policy version required')
    p=policy['parameters']
    for key in ['group_days','need_days','history_days','preferred_days','po_hours','preferred_count','frequency_cap']:
        if type(p.get(key)) is not int or not 0<=p[key]<=10000: raise ValueError(f'Invalid parameter {key}')
    if p['frequency_cap']<1: raise ValueError('frequency_cap must be positive')
    for route,count in p['suggestions'].items():
        if route not in ROUTES or type(count) is not int or not 0<=count<=20: raise ValueError('Invalid suggestion count')
    if len(p['recency_days'])!=2 or not 0<=p['recency_days'][0]<=p['recency_days'][1]: raise ValueError('Invalid recency tiers')
    if set(p['weights'])!={'frequency','recency','contract','delivery','quality'} or any(number(x)<0 for x in p['weights'].values()): raise ValueError('Invalid ranking weights')
    if not policy.get('rules') or len(policy['rules'])>200: raise ValueError('Expected 1–200 rules')
    ids=set(); priorities=set()
    for r in policy['rules']:
        if r['id'] in ids or r['priority'] in priorities: raise ValueError('Duplicate rule ID or priority')
        if type(r['priority']) is not int: raise ValueError('Priority must be integer')
        ids.add(r['id']); priorities.add(r['priority'])
        if r['route'] not in ROUTES: raise ValueError('Unsupported route')
        validate_condition(r['when'])
    return deepcopy(policy)

def validate_policy(policy):
    try: return _validate_policy(policy)
    except (KeyError,TypeError,AttributeError) as exc:
        raise ValueError('Malformed policy: complete version, effective_date, parameters and typed rules are required') from exc

def matches(node, facts):
    if 'all' in node: return all(matches(x,facts) for x in node['all'])
    if 'any' in node: return any(matches(x,facts) for x in node['any'])
    if 'not' in node: return not matches(node['not'],facts)
    key,op=node['fact'],node['op']; a=facts.get(key)
    if op=='exists': return a is not None
    if op=='is_null': return a is None
    if a is None: return False
    a=coerce(key,a)
    if op in {'in','not_in'}:
        result=a in [coerce(key,v) for v in node['value']]
        return result if op=='in' else not result
    b=coerce(key,node['value'])
    return {'eq':lambda:a==b,'ne':lambda:a!=b,'gt':lambda:a>b,'gte':lambda:a>=b,'lt':lambda:a<b,'lte':lambda:a<=b}[op]()

def evaluate(policy, facts):
    trace=[]
    for rule in sorted(policy['rules'],key=lambda r:r['priority']):
        hit=matches(rule['when'],facts); trace.append({'rule':rule['id'],'matched':hit})
        if hit: return rule,trace
    return {'id':'uncovered','route':'NOT_PROCESSED','reason':'No policy rule matched; buyer review required'},trace

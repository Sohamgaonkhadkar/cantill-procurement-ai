"""Plain-language rendering of stored policy data, without financial evaluation."""
import json

FACT_LABELS={
    'item.item_code':'item code','item.item_type':'item type','item.category':'item category',
    'requirement.plant':'plant','requirement.group_value_inr':'requirement value in INR',
    'requirement.is_emergency':'request is an emergency','requirement.total_quantity':'total quantity',
    'requirement.date':'requirement date','contract.has_usable_contract':'an eligible contract has sufficient remaining ceiling',
    'contract.selected_supplier_id':'contract supplier',
    'history.has_active_purchase_365d':'qualifying Active-supplier purchase history exists',
    'history.purchase_count':'qualifying purchase count',
}
ROUTE_LABELS={'CONTRACT_PO':'Contract purchase order','SPOT_PO':'Spot purchase order',
    'EMERGENCY_PO':'Emergency purchase order','RFQ':'Request for quotation (RFQ)',
    'RFP':'Request for proposal (RFP)','NEW_ITEM_SOURCING':'New-item sourcing',
    'CAPEX_SOURCING':'Capital-equipment sourcing','NOT_PROCESSED':'Not processed'}
OPERATORS={'eq':'equals','ne':'does not equal','gt':'is greater than','gte':'is at least',
    'lt':'is below','lte':'is at most','in':'is one of','not_in':'is not one of',
    'exists':'is present','is_null':'is missing'}

def condition_text(node):
    if 'all' in node:return '('+' AND '.join(condition_text(n) for n in node['all'])+')'
    if 'any' in node:return '('+' OR '.join(condition_text(n) for n in node['any'])+')'
    if 'not' in node:return 'NOT ('+condition_text(node['not'])+')'
    label=FACT_LABELS.get(node['fact'],node['fact'].replace('_',' '))
    value=node.get('value');op=node['op']
    if isinstance(value,bool) and op in {'eq','ne'}:
        positive=value if op=='eq' else not value
        return label if positive else 'NOT ('+label+')'
    if op in {'exists','is_null'}:return label+' '+OPERATORS[op]
    if isinstance(value,list):value=', '.join(str(v) for v in value)
    return label+' '+OPERATORS[op]+' '+str(value)

def rule_text(rule):
    return ROUTE_LABELS.get(rule['route'],rule['route'])+': '+condition_text(rule['when'])+'.'

def parameter_text(parameters):
    parts=[]
    for key,label,unit in [('group_days','Grouping window','calendar days'),('need_days','Need-by tolerance on either side of the anchor','days'),('po_hours','PO consolidation window','hours'),('history_days','Purchase-history lookback','days'),('preferred_days','Preferred-supplier history lookback','days')]:
        if key in parameters:parts.append(f'{label}: {parameters[key]} {unit}')
    if parameters.get('weights'):parts.append('Supplier ranking weights: '+', '.join(key.replace('_',' ')+' '+str(value) for key,value in parameters['weights'].items()))
    return '; '.join(parts)+'.' if parts else ''

def policy_text(policy,as_of_date):
    lines=[f"The current procurement policy is version {policy['version']}, effective from {policy['effective_date']} (checked for {as_of_date}).",'Rules are checked in this order; the first matching rule determines the route:']
    lines.extend('- '+rule_text(rule) for rule in sorted(policy['rules'],key=lambda r:r['priority']))
    parameters=parameter_text(policy['parameters'])
    if parameters:lines.append(parameters)
    lines.append('A recommendation does not place an order. An authorized buyer must approve the purchasing action.')
    return '\n\n'.join(lines)

def passage_text(content):
    marker='Complete condition and resulting route: '
    if marker in content:
        try:return rule_text(json.loads(content.split(marker,1)[1]))
        except (ValueError,KeyError,TypeError):pass
    if content.startswith('Policy parameters: '):
        try:return parameter_text(json.loads(content[len('Policy parameters: '):]))
        except (ValueError,KeyError,TypeError):pass
    return content

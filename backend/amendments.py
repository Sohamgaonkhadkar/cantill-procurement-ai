"""Conservative document interpretation; all proposals require human review."""
from copy import deepcopy
import re
from .domain import number
from .policy import validate_policy

def propose(base,text,version,effective_date):
    policy=deepcopy(base)
    policy.pop('status',None)
    policy['version']=version; policy['effective_date']=effective_date
    detected=[]
    # A scoped or conditional clause cannot safely be reduced to a global limit.
    # Preserve its source for structured manual authoring instead of proposing a
    # broader change that a reviewer might mistake for a faithful interpretation.
    if re.search(r'\b(?:plants?|categor(?:y|ies)|only|except|unless|if|when|where|provided|not|never|unchanged)\b',text,re.I):
        validate_policy(policy)
        return policy,detected
    # Only explicitly named numeric limits are interpreted. Other prose remains
    # visible as unresolved source text in the review workflow.
    patterns=[('spot', '5.4','lt'),('emergency','5.3','lte'),('rfq','5.5','lt'),('rfp','5.6','gte')]
    def leaves(node):
        if 'fact' in node: yield node
        for key in ['all','any']:
            for child in node.get(key,[]): yield from leaves(child)
        if 'not' in node: yield from leaves(node['not'])
    for label,rid,op in patterns:
        # Match the whole statement, not a fragment that might omit scope,
        # exceptions, negation, a previous amount, or an operator change.
        match=re.fullmatch(r'\s*(?:(?:please|change|set|update|revise|increase|decrease|reduce|the|new)\s+)*'+label+r'\s+(?:PO\s+)?(?:limit|threshold)\s*(?:to|of|is|=|:)?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore)?\s*\.?\s*',text,re.I)
        if match:
            amount=number(match[1]); multiplier={'lakh':100000,'lac':100000,'crore':10000000}.get((match[2] or '').lower(),1); amount*=multiplier
            for rule in policy['rules']:
                if rule['id']==rid:
                    for leaf in leaves(rule['when']):
                        if leaf['fact']=='requirement.group_value_inr': leaf['value']=str(amount)
            if label in {'rfq','rfp'}:
                for rule in policy['rules']:
                    if rule['id'] in {'5.5','5.6'}:
                        for leaf in leaves(rule['when']):
                            if leaf['fact']=='requirement.group_value_inr': leaf['value']=str(amount)
            detected.append(f'{label} threshold proposed: INR {amount}')
    validate_policy(policy)
    return policy,detected

def field_diff(before,after,path=''):
    if isinstance(before,dict) and isinstance(after,dict):
        return [d for k in sorted(set(before)|set(after)) for d in field_diff(before.get(k),after.get(k),f'{path}.{k}' if path else k)]
    if before!=after: return [{'path':path,'before':before,'after':after}]
    return []

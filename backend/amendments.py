"""Amendment compatibility entrypoint and precise policy diffs."""
from itertools import zip_longest
from .language import interpret

def propose(base,text,version,effective_date):
    result=interpret(base,text,version,effective_date)
    return result['policy'],result['detected_changes']

def field_diff(before,after,path=''):
    if isinstance(before,dict) and isinstance(after,dict):
        return [d for k in sorted(set(before)|set(after)) for d in field_diff(before.get(k),after.get(k),f'{path}.{k}' if path else k)]
    if isinstance(before,list) and isinstance(after,list):
        combined=before+after
        if combined and all(isinstance(x,dict) and isinstance(x.get('id'),str) for x in combined) and len({x['id'] for x in before})==len(before) and len({x['id'] for x in after})==len(after):
            old={x['id']:x for x in before}; new={x['id']:x for x in after}
            return [d for key in sorted(set(old)|set(new)) for d in field_diff(old.get(key),new.get(key),f'{path}[{key}]')]
        return [d for i,(a,b) in enumerate(zip_longest(before,after)) for d in field_diff(a,b,f'{path}[{i}]')]
    if before!=after: return [{'path':path,'before':before,'after':after}]
    return []

def policy_diff(before,after):
    # Governance has its own audit trail. Embedding its prior diff recursively
    # would duplicate historical source documents with each new policy version.
    excluded={'id','status','governance'}
    return field_diff({k:v for k,v in before.items() if k not in excluded},{k:v for k,v in after.items() if k not in excluded})

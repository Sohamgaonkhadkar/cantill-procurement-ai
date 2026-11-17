"""Bounded symbolic overlap checks for the existing typed predicate DSL.

Witnesses are possible fact combinations, not fabricated purchasing records.
This deliberately over-approximates relationships between master-data facts.
Simulation against real snapshots remains the business-impact check.
"""
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal
from .policy import FACTS,matches
from .domain import number

class AnalysisBound(ValueError):pass

def dnf(node,negated=False):
    if 'not' in node:return dnf(node['not'],not negated)
    logical=next((key for key in ['all','any'] if key in node),None)
    if not logical:return [[(node,negated)]]
    conjunction=(logical=='all')!=negated
    parts=[dnf(child,negated) for child in node[logical]]
    result=[[]] if conjunction else []
    for part in parts:
        result=[a+b for a in result for b in part] if conjunction else result+part
        if len(result)>128 or any(len(branch)>128 for branch in result):raise AnalysisBound()
    return result

def witness(left,right):
    count=0
    for a in dnf(left):
        for b in dnf(right):
            count+=1
            if count>512:raise AnalysisBound()
            facts={};by_fact=defaultdict(list)
            for node,negated in a+b:by_fact[node['fact']].append((node,negated))
            for fact,tests in by_fact.items():
                typ=FACTS[fact];values=[]
                for node,_ in tests:
                    value=node.get('value')
                    values.extend(value if isinstance(value,list) else [value])
                if typ is Decimal:
                    values=[number(v) for v in values if v is not None]
                    values=[Decimal(0),Decimal(1),*values,*[v+delta for v in values for delta in [Decimal('-0.000000000001'),Decimal('0.000000000001')]]]
                elif typ is date:
                    values=[date.fromisoformat(v) for v in values if v is not None]
                    values=[date(2026,1,1),*values,*[v+timedelta(days=d) for v in values for d in [-1,1]]]
                elif typ is bool:values=[True,False]
                else:values=[*values,'__OTHER__']
                values.append(None)
                found=False
                for value in values:
                    try:
                        if all(matches(node,{fact:value})!=negated for node,negated in tests):
                            facts[fact]=value;found=True;break
                    except (ValueError,TypeError):continue
                if not found:break
            else:
                return {key:(str(value) if isinstance(value,(Decimal,date)) else value) for key,value in facts.items()}
    return False

def analyze(base,policy):
    original={r['id']:r for r in base['rules']};changed=[];warnings=[];complete=True;comparisons=0
    for rule in policy['rules']:
        old=original.get(rule['id'])
        if old and all(old[k]==rule[k] for k in ['when','priority','route']):continue
        changed.append(rule['id'])
        for other in policy['rules']:
            if other['id']==rule['id']:continue
            comparisons+=1
            if comparisons>2000:complete=False;break
            try:example=witness(rule['when'],other['when'])
            except (AnalysisBound,ValueError,KeyError,TypeError):example=None;complete=False
            if example is False:continue
            earlier=rule if rule['priority']<other['priority'] else other
            later=other if earlier is rule else rule
            warnings.append({'rule_id':rule['id'],'earlier_rule':earlier['id'],'earlier_route':earlier['route'],'later_rule':later['id'],'later_route':later['route'],'direction':'new_shadows_existing' if earlier is rule else 'existing_shadows_new','priority':rule['priority'],'possible_facts':example,'certainty':'possible_fact_overlap' if example is not None else 'analysis_bound','message':f"{earlier['id']} ({earlier['route']}) can match before {later['id']} ({later['route']}). Inspect scope and simulate the affected requests.", 'requires_acknowledgement':old is None or old['priority']!=rule['priority'] or later['route'] in {'CAPEX_SOURCING','CONTRACT_PO','EMERGENCY_PO'}})
            if len(warnings)>=256:complete=False;break
        if comparisons>2000 or len(warnings)>=256:break
    return {'changed_rules':changed,'warnings':warnings,'complete':complete,'requires_acknowledgement':not complete or any(w['requires_acknowledgement'] for w in warnings),'note':'Conservative symbolic overlaps, not actual procurement decisions. Real-data simulation establishes business impact.'}

"""Stable transport schemas for Arena and generated OpenAPI clients."""
from pydantic import BaseModel,ConfigDict,Field
from typing import Any,Literal

class Schema(BaseModel): model_config=ConfigDict(extra='allow')
class PolicyParameters(Schema):
    group_days:int
    need_days:int
    history_days:int
    preferred_days:int
    po_hours:int
    preferred_count:int
    suggestions:dict[str,int]
    weights:dict[str,int|float]
    recency_days:list[int]
    frequency_cap:int
class Predicate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    fact:str=Field(description='One of the facts returned by /api/policy-schema')
    op:Literal['eq','ne','gt','gte','lt','lte','in','not_in','exists','is_null']
    value:Any=None
class AllCondition(BaseModel):
    model_config=ConfigDict(extra='forbid')
    all:list['Predicate | AllCondition | AnyCondition | NotCondition']
class AnyCondition(BaseModel):
    model_config=ConfigDict(extra='forbid')
    any:list['Predicate | AllCondition | AnyCondition | NotCondition']
class NotCondition(BaseModel):
    model_config=ConfigDict(extra='forbid',populate_by_name=True)
    negated:'Predicate | AllCondition | AnyCondition | NotCondition'=Field(alias='not')
class PolicyRule(Schema):
    id:str
    priority:int
    when:Predicate|AllCondition|AnyCondition|NotCondition
    route:Literal['CAPEX_SOURCING','CONTRACT_PO','EMERGENCY_PO','SPOT_PO','RFQ','RFP','NEW_ITEM_SOURCING','NOT_PROCESSED']
    reason:str
class PolicyDefinition(Schema):
    version:str
    effective_date:str
    parameters:PolicyParameters
    rules:list[PolicyRule]
class OutputRow(Schema):
    pr_no:str
    pr_line:str
    resolved_item_code:str
    group_id:str
    po_id:str
    decision:str
    route:str
    supplier_id:str
    unit_price:str
    group_value_inr:str
    suggested_supplier_ids:str
    policy_version:str
    reason:str
class ValuationEvidence(Schema):
    unit_price:str
    source:str
    reference:str
    quantity:str
    exact_value:str
    lookback_days:int
class ContractEvidence(Schema):
    contract_id:str
    supplier_id:str
    rate:str
    remaining:str
    required:str
    applicable:bool
    usable:bool
    rejection:str|None
class Ranking(Schema):
    supplier_id:str
    name:str
    purchase_count:int
    last_purchase:str|None
    contract_history:bool
    reference_price:str
    reference_source:str
    components:dict[str,str]
    score:str
class Evidence(Schema):
    facts:dict[str,Any]
    rule_trace:list[dict]
    valuation:ValuationEvidence
    contracts:list[ContractEvidence]
    ranking:list[Ranking]
    order_reference:str
    selected_contract:str|None
    group_anchor:dict[str,str]
    grouping:str
    matching:list[dict]
    po_anchor:str|None=None
class RequirementResponse(Schema):
    id:str
    item_code:str
    description:str
    plant:str
    created_at:str
    need_by_date:str
    quantity:str
    decision:str
    route:str
    supplier_id:str
    unit_price:str
    group_value_inr:str
    suggested_supplier_ids:str
    policy_version:str
    reason:str
    po_id:str
    evidence:Evidence
    lines:list[dict[str,str]]
    approval_status:str
class ProcessingResult(Schema):
    rows:list[OutputRow]
    requirements:list[RequirementResponse]
    orders:list[dict]
    allocations:dict[str,str]
    issues:list[dict]
    output_hash:str
    counts:dict[str,int]
class RunResponse(ProcessingResult):
    id:str
    created_at:str
    input_hash:str
    data_hash:str
    policy_hash:str
    policy_snapshots:list[dict]
    explicit_policy:str|None
    input:list[dict[str,str]]
    status:Literal['completed']
    actor:str
class Page(Schema):
    items:list[dict]
    total:int
    offset:int
    limit:int
class LoginResponse(Schema):
    access_token:str
    token_type:Literal['bearer']
    role:str
    expires_in:int
class PolicyResponse(PolicyDefinition):
    id:str
    version:str
    effective_date:str
    status:str
class ComparisonResponse(Schema):
    affected_lines:int
    explanation_changes:int
    changes:list[dict]
class SimulationResponse(Schema):
    simulation:Literal[True]
    policy_id:str
    base_run_id:str
    result:ProcessingResult
    comparison:ComparisonResponse
class ActionResponse(Schema):
    id:str
    run_id:str
    requirements:list[str]
    recommendations:list[RequirementResponse]
    actor:str
    approved_at:str
    reason:str
    status:str
class ChatResponse(Schema):
    session_id:str
    message:str
    state:dict
    alternatives:list[dict]
    run:RunResponse|None
    messages:list[dict]

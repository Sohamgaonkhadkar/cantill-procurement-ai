from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

Intent=Literal['create_purchase_request','correct_purchase_request','confirm_purchase_request','cancel_purchase_request','policy_question','contract_question','supplier_question','decision_explanation','general_procurement_question','unsupported']

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')

class DraftPatch(Strict):
    description:str|None=None
    item_code:str|None=None
    quantity:str|None=None
    uom:str|None=None
    plant:str|None=None
    need_by_date:str|None=None
    urgency:Literal['Normal','Emergency']|None=None
    estimated_unit_price:str|None=None

class FieldEvidence(Strict):
    description:str|None=None
    item_code:str|None=None
    quantity:str|None=None
    uom:str|None=None
    plant:str|None=None
    need_by_date:str|None=None
    urgency:str|None=None
    estimated_unit_price:str|None=None

class IntentPlan(Strict):
    intent:Intent
    updates:DraftPatch=Field(default_factory=DraftPatch)
    evidence:FieldEvidence=Field(default_factory=FieldEvidence)
    clear_fields:list[Literal['item_code','quantity','plant','need_by_date','urgency','uom','estimated_unit_price']]=Field(default_factory=list,max_length=7)
    missing_fields:list[str]=Field(default_factory=list,max_length=8)
    ambiguous_fields:list[str]=Field(default_factory=list,max_length=8)
    clarification:str=Field('',max_length=600)

class Citation(Strict):
    id:str
    title:str
    source_type:str
    source_id:str
    policy_version:str|None=None
    clause:str|None=None
    page:int|None=None
    effective_date:str|None=None
    content_hash:str
    excerpt:str
    href:str

class GroundedAnswer(Strict):
    answer:str=Field(max_length=3000)
    citation_ids:list[str]=Field(max_length=8)
    insufficient_evidence:bool
    suggested_followups:list[str]=Field(max_length=3)

class SourceInput(Strict):
    title:str=Field(min_length=1,max_length=200)
    source_type:Literal['guideline','policy_document','contract_document','public_document']
    policy_version:str|None=Field(None,max_length=128)
    contract_id:str|None=Field(None,max_length=128)
    effective_date:str|None=None
    expires_at:str|None=None
    visibility:Literal['owner','workspace']='owner'
    classification:Literal['private','public_approved']='private'
    public_url:str|None=Field(None,max_length=1000)

class SourceReview(Strict):
    reason:str=Field(min_length=10,max_length=2000)
    approve_external_public_processing:bool=False

class AIStatus(Strict):
    chat_enabled:bool
    rag_enabled:bool
    external_eligible:bool
    provider:str|None
    model:str|None
    configuration_status:Literal['configured','missing_gemini_api_key','local_only']
    requires_fictional_acknowledgement:bool
    live_data_external_calls:Literal[False]

class KnowledgeSource(BaseModel):
    model_config=ConfigDict(extra='allow')
    id:str
    source_key:str
    source_hash:str
    owner_id:str|None
    classification:Literal['private','fictional_demo','public_approved']
    status:str
    updated_at:str
    title:str
    source_type:str
    visibility:Literal['owner','workspace']
    external_approved:bool

class KnowledgePage(Strict):
    items:list[KnowledgeSource]
    total:int
    offset:int
    limit:int

class KnowledgeMatch(Strict):
    citation:Citation
    content:str
    score:float
    classification:str
    external_approved:bool
    document_id:str

class KnowledgeSearch(Strict):
    items:list[KnowledgeMatch]
    as_of_date:str
    retrieval:str

class KnowledgeChunkResponse(Strict):
    citation:Citation
    content:str
    status:str
    classification:str

class SourceSnapshot(Strict):
    citation:Citation
    snapshot:Literal[True]

class ReindexResult(Strict):
    documents:int
    external_calls:Literal[False]

class EmbeddingResult(Strict):
    embedded_chunks:int
    model:str
    idempotent:bool

class UsageEntry(Strict):
    id:str
    created_at:str
    model:str
    status:str
    input_tokens:int
    output_tokens:int
    cost_usd:str
    token_count_estimated:bool=False

class UsagePage(Strict):
    items:list[UsageEntry]
    total:int
    offset:int
    limit:int

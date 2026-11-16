"""Versioned local ingestion. This module performs no model/network calls."""
from copy import deepcopy
from datetime import date
import hashlib,json,re
from sqlalchemy import select
from ..db import KnowledgeDocument,KnowledgeChunk,Policy,Contract,Item,now
from ..domain import digest
from ..workspace import isolated_demo
from ..policy import initial_policy
from ..db import transaction_lock

def lock_source(session,source_key):
    # Serialize revisions across serverless workers, independently of the
    # process-local API lock. Source keys are immutable and server generated.
    transaction_lock(session,1000000000+int(digest(source_key)[:14],16),exclusive=True)

def store_document(session,source_key,title,sections,*,owner_id=None,classification='private',status='approved',metadata=None,source_hash=None):
    lock_source(session,source_key)
    metadata=metadata or {}
    if len(sections)>500:raise ValueError('At most 500 source sections per document')
    if classification not in {'private','fictional_demo','public_approved'}:raise ValueError('Unknown source classification')
    if classification=='fictional_demo' and not isolated_demo():raise ValueError('Fictional demo sources belong only in their isolated workspace')
    source_hash=source_hash or digest(sections)
    key='DOC-'+digest([source_key,source_hash])[:32]
    existing=session.get(KnowledgeDocument,key)
    if existing:
        if status=='approved':
            for prior in session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.source_key==source_key,KnowledgeDocument.id!=key,KnowledgeDocument.status=='approved')):prior.status='superseded'
        existing.status=status
        existing.payload={**existing.payload,**metadata,'title':title}
        return existing
    # Supersede earlier contents of a mutable source, never mix revisions.
    if status=='approved':
        for prior in session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.source_key==source_key,KnowledgeDocument.status=='approved')):
            prior.status='superseded'
    document=KnowledgeDocument(id=key,source_key=source_key,source_hash=source_hash,owner_id=owner_id,classification=classification,status=status,updated_at=now(),payload={'title':title,'visibility':'workspace' if owner_id is None else 'owner','external_approved':False,**metadata})
    session.add(document);session.flush()
    for ordinal,section in enumerate(sections):
        content=section['content'].strip()
        if not content:continue
        if len(content)>16000:raise ValueError('A source section is too large; split at its semantic section boundary')
        content_hash=hashlib.sha256(content.encode()).hexdigest()
        session.add(KnowledgeChunk(id='KCH-'+digest([key,ordinal,content_hash])[:32],document_id=key,ordinal=ordinal,content=content,content_hash=content_hash,embedding=None,embedding_model=None,payload={k:v for k,v in section.items() if k!='content'}))
    session.flush()
    return document

def index_policy(session,policy,status):
    if status not in {'active','approved','superseded'}:return None
    core={k:deepcopy(policy[k]) for k in ['version','effective_date','parameters','rules']}
    baseline=initial_policy()
    trusted_demo=isolated_demo() and all(core[k]==baseline[k] for k in ['version','effective_date','rules','parameters'])
    sections=[{'section':'parameters','content':'Policy parameters: '+json.dumps(core['parameters'],sort_keys=True)}]
    for rule in core['rules']:
        sections.append({'section':rule['id'],'clause':rule['id'],'content':f"Policy {core['version']}, rule {rule['id']}: {rule['reason']}. Complete condition and resulting route: "+json.dumps(rule,sort_keys=True)})
    return store_document(session,'policy:'+core['version'],('Fictional demo policy ' if trusted_demo else 'Procurement policy ')+core['version'],sections,classification='fictional_demo' if trusted_demo else 'private',metadata={'source_type':'policy','policy_version':core['version'],'effective_date':core['effective_date'],'policy_status':status,'external_approved':trusted_demo,'visibility':'workspace'},source_hash=digest(core))

def sync_core_sources(session):
    count=0
    for policy in session.scalars(select(Policy).order_by(Policy.id)):
        if index_policy(session,policy.payload,policy.status):count+=1
    if isolated_demo():
        from ..demo import dataset
        trusted=dataset()
    else:trusted=None
    for item in session.scalars(select(Item).order_by(Item.id)):
        payload=deepcopy(item.payload)
        demo=bool(trusted and trusted.items.get(item.id)==payload)
        store_document(session,'catalog:'+item.id,'Catalog item '+item.id,[{'section':'specification','content':json.dumps(payload,sort_keys=True)}],classification='fictional_demo' if demo else 'private',metadata={'source_type':'catalog','item_code':item.id,'external_approved':demo,'visibility':'workspace'},source_hash=digest(payload));count+=1
    for contract in session.scalars(select(Contract).order_by(Contract.id)):
        # Live headroom, ledger consumption and raw private PDF text are never
        # embedded. They are fetched from the authoritative read-only tools.
        payload={k:deepcopy(contract.payload[k]) for k in ['contract_id','supplier_id','start_date','end_date','value_cap','lines']}
        source=next((c for c in trusted.contracts if c['contract_id']==contract.id),None) if trusted else None
        demo=bool(source and all(source[k]==payload[k] for k in payload))
        store_document(session,'contract:'+contract.id,'Contract '+contract.id,[{'section':'validated terms','content':json.dumps(payload,sort_keys=True)}],classification='fictional_demo' if demo else 'private',metadata={'source_type':'contract','contract_id':contract.id,'effective_date':payload['start_date'],'expires_at':payload['end_date'],'external_approved':demo,'visibility':'workspace'},source_hash=digest(payload));count+=1
    return count

def text_sections(text):
    """Preserve paragraphs/clauses instead of slicing thresholds from exceptions."""
    groups=re.split(r'\n\s*\n',text.strip())
    result=[];current=[];size=0
    for paragraph in groups:
        if len(paragraph)>16000:raise ValueError('Oversized unstructured paragraph; provide sectioned text')
        if size+len(paragraph)>3500 and current:
            result.append({'section':str(len(result)+1),'content':'\n\n'.join(current)});current=[];size=0
        current.append(paragraph);size+=len(paragraph)
    if current:result.append({'section':str(len(result)+1),'content':'\n\n'.join(current)})
    return result

def pdf_sections(raw):
    from io import BytesIO
    from pypdf import PdfReader
    reader=PdfReader(BytesIO(raw),strict=True)
    if len(reader.pages)>100:raise ValueError('Knowledge PDFs are limited to 100 pages')
    result=[]
    for page_number,page in enumerate(reader.pages,1):
        for section in text_sections(page.extract_text() or ''):result.append({**section,'page':page_number})
    if not result:raise ValueError('No readable PDF text; provide a transcription for review')
    return result

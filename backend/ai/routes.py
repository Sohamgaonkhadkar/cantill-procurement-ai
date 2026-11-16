"""Authenticated local knowledge governance. No ingestion makes network calls."""
from datetime import date
from hashlib import sha256
import json
from fastapi import APIRouter,Depends,UploadFile,File,Form,Query,HTTPException
from sqlalchemy import select,func,text
from ..db import KnowledgeDocument,KnowledgeChunk,Chat,Policy,AIUsage
from ..domain import digest
from ..security import user,require_owner,require
from ..service import audit
from .schemas import SourceInput,SourceReview
from .schemas import AIStatus,KnowledgeSource,KnowledgePage,KnowledgeSearch,KnowledgeChunkResponse,SourceSnapshot,ReindexResult,EmbeddingResult,UsagePage
from .knowledge import store_document,text_sections,pdf_sections,sync_core_sources
from .retrieval import search,can_read,citation
from .safety import authorize_actor,ExternalContext
from .tools import today
from .config import settings
from .provider import Provider

def install(app,factory,lock):
    router=APIRouter(prefix='/api',tags=['Knowledge'])

    @router.get('/ai/status',response_model=AIStatus)
    def status(actor=Depends(user)):
        from ..workspace import isolated_demo
        config=settings()
        from .provider import credential
        from .config import flag
        eligible=isolated_demo() and flag('AI_EXTERNAL_CALLS_ENABLED')
        return {'chat_enabled':config.enabled,'rag_enabled':config.rag_enabled,'external_eligible':eligible,'provider':config.provider if isolated_demo() else None,'model':config.model if isolated_demo() else None,'configuration_status':'configured' if eligible and credential() else ('missing_gemini_api_key' if eligible else 'local_only'),'requires_fictional_acknowledgement':True,'live_data_external_calls':False}

    @router.post('/knowledge/reindex',response_model=ReindexResult)
    def reindex(actor=Depends(user)):
        require_owner(actor)
        with lock,factory().begin() as session:
            authorize_actor(session,actor);count=sync_core_sources(session)
            audit(session,actor,'knowledge.reindexed',{'documents':count,'external_calls':False})
        return {'documents':count,'external_calls':False}

    @router.post('/knowledge/documents',response_model=KnowledgeSource)
    async def upload(file:UploadFile=File(...),metadata:str=Form(...,description='JSON-encoded source metadata. Ingestion stays local and creates a draft requiring review.',json_schema_extra={'contentMediaType':'application/json','contentSchema':SourceInput.model_json_schema()}),actor=Depends(user)):
        require_owner(actor)
        from ..api import content
        raw=await content(file,{'.txt','.pdf'})
        meta=SourceInput.model_validate_json(metadata)
        for value in [meta.effective_date,meta.expires_at]:
            if value:date.fromisoformat(value)
        if meta.effective_date and meta.expires_at and meta.effective_date>meta.expires_at:raise ValueError('Expiry precedes effective date')
        if meta.source_type=='policy_document' and not meta.policy_version:raise ValueError('Policy documents require a version')
        if meta.classification=='public_approved' and not (meta.public_url or '').startswith('https://'):raise ValueError('Public documentation requires its HTTPS provenance URL; the server does not fetch it')
        try:sections=pdf_sections(raw) if file.filename.lower().endswith('.pdf') else text_sections(raw.decode('utf-8-sig'))
        except UnicodeError:raise ValueError('Text source must use UTF-8') from None
        if not sections:raise ValueError('Document is empty')
        fingerprint=sha256(raw).hexdigest()
        with lock,factory().begin() as session:
            authorize_actor(session,actor)
            if meta.policy_version and not session.get(Policy,meta.policy_version):raise ValueError('Unknown policy version')
            key='upload:'+str(actor)+':'+digest([meta.title,meta.source_type])[:24]
            existing=session.scalar(select(KnowledgeDocument).where(KnowledgeDocument.source_key==key,KnowledgeDocument.source_hash==fingerprint))
            if existing:return _document(existing)
            doc=store_document(session,key,meta.title,sections,owner_id=str(actor),classification=meta.classification,status='draft',metadata={**meta.model_dump(),'external_approved':False,'uploaded_by':str(actor),'filename':file.filename},source_hash=fingerprint)
            audit(session,actor,'knowledge.uploaded',{'document_id':doc.id,'source_hash':fingerprint})
            return _document(doc)

    @router.get('/knowledge/documents',response_model=KnowledgePage)
    def documents(offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),actor=Depends(user)):
        require_owner(actor)
        with factory()() as session:
            statement=select(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc(),KnowledgeDocument.id)
            count=session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
            return {'items':[_document(d) for d in session.scalars(statement.offset(offset).limit(limit))],'total':count,'offset':offset,'limit':limit}

    @router.post('/knowledge/documents/{document_id}/review',response_model=KnowledgeSource)
    def review(document_id:str,body:SourceReview,actor=Depends(user)):
        require_owner(actor)
        with lock,factory().begin() as session:
            authorize_actor(session,actor)
            doc=session.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id==document_id).with_for_update())
            if not doc:raise HTTPException(404,'Document not found')
            if doc.status!='draft':raise HTTPException(409,'Only draft sources can be reviewed')
            if body.approve_external_public_processing and doc.classification!='public_approved':raise ValueError('Private sources cannot be approved for external processing')
            for prior in session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.source_key==doc.source_key,KnowledgeDocument.id!=doc.id,KnowledgeDocument.status=='approved')):prior.status='superseded'
            doc.status='approved';doc.payload={**doc.payload,'external_approved':body.approve_external_public_processing,'reviewed_by':str(actor),'review_reason':body.reason}
            audit(session,actor,'knowledge.reviewed',{'document_id':doc.id,'external_approved':doc.payload['external_approved']})
            return _document(doc)

    @router.get('/knowledge/search',response_model=KnowledgeSearch)
    def query(q:str=Query(min_length=1,max_length=500),policy_version:str|None=None,as_of_date:date|None=None,actor=Depends(user)):
        with factory()() as session:
            authorize_actor(session,actor)
            results=search(session,actor,q,as_of_date or today(),policy_version=policy_version,top_k=settings().top_k)
        return {'items':results,'as_of_date':str(as_of_date or today()),'retrieval':'local_exact_and_lexical'}

    @router.get('/knowledge/chunks/{chunk_id}',response_model=KnowledgeChunkResponse)
    def chunk(chunk_id:str,actor=Depends(user)):
        with factory()() as session:
            authorize_actor(session,actor);part=session.get(KnowledgeChunk,chunk_id)
            doc=session.get(KnowledgeDocument,part.document_id) if part else None
            if not doc or not can_read(doc,actor):raise HTTPException(404,'Source not found')
            return {'citation':citation(part,doc),'content':part.content,'status':doc.status,'classification':doc.classification}

    @router.get('/chat/sessions/{session_id}/sources/{source_id}',response_model=SourceSnapshot)
    def chat_source(session_id:str,source_id:str,actor=Depends(user)):
        with factory()() as session:
            authorize_actor(session,actor);record=session.get(Chat,session_id)
            if not record or record.payload['actor']!=str(actor):raise HTTPException(404,'Source not found')
            source=record.payload.get('sources',{}).get(source_id)
            if not source:raise HTTPException(404,'Source not found')
            return {'citation':source,'snapshot':True}

    @router.get('/ai/usage',response_model=UsagePage)
    def usage(offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),actor=Depends(user)):
        with factory()() as session:
            authorize_actor(session,actor)
            stmt=select(AIUsage).where(AIUsage.actor==str(actor)).order_by(AIUsage.created_at.desc(),AIUsage.id)
            total=session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
            return {'items':[{'id':r.id,'created_at':r.created_at,'model':r.model,'status':r.status,'input_tokens':r.input_tokens,'output_tokens':r.output_tokens,'cost_usd':r.cost_usd,'token_count_estimated':r.payload.get('token_count_estimated',False)} for r in session.scalars(stmt.offset(offset).limit(limit))],'total':total,'offset':offset,'limit':limit}

    @router.post('/knowledge/documents/{document_id}/embed',response_model=EmbeddingResult)
    def embed(document_id:str,actor=Depends(user)):
        # Public demo admins may embed only already approved, explicitly
        # external-safe sources. Upload/review/reindex remain owner controls.
        require(actor,'admin')
        with factory()() as session:
            authorize_actor(session,actor);doc=session.get(KnowledgeDocument,document_id)
            if not doc or doc.status!='approved':raise HTTPException(404,'Approved source not found')
            if not doc.payload.get('external_approved'):raise ValueError('Source is not approved for external processing')
            chunks=list(session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.document_id==doc.id).order_by(KnowledgeChunk.ordinal)))
            pending=[(c.id,c.content,c.content_hash) for c in chunks if not c.embedding or c.embedding_model!=settings().embedding_model]
            pending=pending[:12]
            classification=doc.classification;source_hash=doc.source_hash
        if not pending:return {'embedded_chunks':0,'model':settings().embedding_model,'idempotent':True}
        # SDK calls are outside the read transaction. Provider rechecks the
        # isolated demo boundary, provenance and explicit embedding flag.
        vectors=[];provider=Provider(factory(),actor)
        context=ExternalContext(True,(classification,),True)
        for start in range(0,len(pending),4):vectors.extend(provider.embed([c[1] for c in pending[start:start+4]],context))
        with lock,factory().begin() as session:
            authorize_actor(session,actor);doc=session.get(KnowledgeDocument,document_id)
            if not doc or doc.status!='approved' or doc.source_hash!=source_hash or not doc.payload.get('external_approved'):raise HTTPException(409,'Source changed while embedding')
            vector_schema=None
            if session.bind.dialect.name=='postgresql' and session.scalar(text("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='knowledge_chunks' AND column_name='embedding_vector')")):
                vector_schema=session.scalar(text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'"))
            for (chunk_id,_,content_hash),vector in zip(pending,vectors):
                part=session.get(KnowledgeChunk,chunk_id)
                if not part or part.content_hash!=content_hash:raise HTTPException(409,'Source chunk changed')
                part.embedding=vector;part.embedding_model=settings().embedding_model
                if vector_schema:
                    quoted=session.bind.dialect.identifier_preparer.quote(vector_schema)
                    session.execute(text(f'UPDATE knowledge_chunks SET embedding_vector=CAST(:vector AS {quoted}.vector) WHERE id=:id'),{'vector':json.dumps(vector),'id':part.id})
            audit(session,actor,'knowledge.embedded',{'document_id':document_id,'chunks':len(pending),'model':settings().embedding_model})
        return {'embedded_chunks':len(pending),'model':settings().embedding_model,'idempotent':False}

    app.include_router(router)

def _document(doc):
    return {'id':doc.id,'source_key':doc.source_key,'source_hash':doc.source_hash,'owner_id':doc.owner_id,'classification':doc.classification,'status':doc.status,'updated_at':doc.updated_at,**doc.payload}

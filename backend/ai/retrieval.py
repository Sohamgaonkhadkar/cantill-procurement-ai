"""Authorized exact, PostgreSQL full-text and optional semantic retrieval."""
from datetime import date
from math import sqrt
import re
from sqlalchemy import select,or_,func,literal_column,text
from ..db import KnowledgeDocument,KnowledgeChunk,Policy
from ..domain import digest
from ..engine import select_policy
from ..service import policies
from .schemas import Citation

STOP={'what','which','when','why','how','is','are','the','a','an','our','we','do','does','for','of','to','in','and','about','please','can','you'}
ALIASES={'rfq':['quotation','quotes'],'rfp':['proposal'],'spot':['spot_po'],'emergency':['emergency_po'],'capex':['capital'],'grouping':['group','group_days'],'limit':['threshold','value'],'purchasing':['purchase'],'blocked':['active','status']}

def terms(query):
    found=[t for t in re.findall(r'[a-z0-9][a-z0-9_.-]*',query.lower()) if t not in STOP]
    return list(dict.fromkeys(found+[alias for term in found for alias in ALIASES.get(term,[])]))[:30]

def can_read(document,actor):
    return document.status=='approved' and (document.payload.get('visibility')=='workspace' or document.owner_id==str(actor))

def authorized_statement(actor,as_of,policy_version=None,source_type=None,include_expired=False):
    statement=select(KnowledgeChunk,KnowledgeDocument).join(KnowledgeDocument,KnowledgeChunk.document_id==KnowledgeDocument.id).where(KnowledgeDocument.status=='approved',or_(KnowledgeDocument.payload['visibility'].as_string()=='workspace',KnowledgeDocument.owner_id==str(actor)))
    if source_type:
        kinds={'policy':['policy','policy_document'],'contract':['contract','contract_document']}.get(source_type,[source_type])
        statement=statement.where(KnowledgeDocument.payload['source_type'].as_string().in_(kinds))
    day=as_of.isoformat()
    statement=statement.where(or_(KnowledgeDocument.payload['effective_date'].as_string().is_(None),KnowledgeDocument.payload['effective_date'].as_string()<=day))
    if not include_expired:statement=statement.where(or_(KnowledgeDocument.payload['expires_at'].as_string().is_(None),KnowledgeDocument.payload['expires_at'].as_string()>=day))
    if policy_version:
        statement=statement.where(or_(KnowledgeDocument.payload['source_type'].as_string().not_in(['policy','policy_document']),KnowledgeDocument.payload['policy_version'].as_string()==policy_version))
    return statement

def citation(chunk,document):
    meta=document.payload;part=chunk.payload
    return Citation(id=chunk.id,title=meta['title'],source_type=meta.get('source_type','document'),source_id=document.source_key,policy_version=meta.get('policy_version'),clause=part.get('clause'),page=part.get('page'),effective_date=meta.get('effective_date'),content_hash=chunk.content_hash,excerpt=chunk.content[:1800],href='/api/knowledge/chunks/'+chunk.id).model_dump()

def cosine(left,right):
    if not left or not right or len(left)!=len(right):return 0.0
    denominator=sqrt(sum(v*v for v in left))*sqrt(sum(v*v for v in right))
    return sum(a*b for a,b in zip(left,right))/denominator if denominator else 0.0

def search(session,actor,query,as_of,*,policy_version=None,source_type=None,query_embedding=None,embedding_model=None,top_k=5):
    try:selected=select_policy(policies(session),as_of,policy_version)
    except ValueError:selected=None
    # Only an effective, enforced policy is represented as current policy.
    if source_type=='policy' and not selected:return []
    version=selected['version'] if selected else '__no_effective_policy__'
    statement=authorized_statement(actor,as_of,version,source_type)
    candidates=list(session.execute(statement.order_by(KnowledgeChunk.id).limit(500)))
    words=terms(query)
    if not words:return []
    scores={chunk.id:0.0 for chunk,_ in candidates};by_id={c.id:(c,d) for c,d in candidates}
    exact=[];lexical=[];semantic=[]
    for chunk,document in candidates:
        identifiers=[document.source_key,*[str(document.payload.get(k,'')) for k in ['contract_id','policy_version','item_code']],str(chunk.payload.get('clause',''))]
        if any(value and re.search(r'(?<![\w.-])'+re.escape(value)+r'(?![\w.-])',query,re.I) for value in identifiers):exact.append(chunk.id)
        content=chunk.content.lower();rank=sum(1+min(content.count(word),4)*.1 for word in words if word in content)
        if rank:lexical.append((rank,chunk.id))
        if query_embedding and chunk.embedding and chunk.embedding_model==embedding_model:semantic.append((cosine(query_embedding,chunk.embedding),chunk.id))
    if session.bind.dialect.name=='postgresql':
        # Parameterized lexical query, after the same authorization/date filters.
        tsquery=func.websearch_to_tsquery('simple',' OR '.join(words))
        vector=func.to_tsvector('simple',KnowledgeChunk.content)
        rows=session.execute(statement.where(vector.op('@@')(tsquery)).order_by(func.ts_rank_cd(vector,tsquery).desc()).limit(40)).all()
        if rows:lexical=[(len(rows)-i,c.id) for i,(c,_) in enumerate(rows)]
        for chunk,document in rows:by_id[chunk.id]=(chunk,document);scores.setdefault(chunk.id,0.0)
        if query_embedding:
            has_vector=session.scalar(text("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='knowledge_chunks' AND column_name='embedding_vector')"))
            if has_vector:
                namespace=session.scalar(text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'"))
                if namespace:
                    quoted=session.bind.dialect.identifier_preparer.quote(namespace)
                    distance=literal_column('knowledge_chunks.embedding_vector').op(f'OPERATOR({quoted}.<=>)')(text(f'CAST(:query_vector AS {quoted}.vector)'))
                    rows=session.execute(statement.where(KnowledgeChunk.embedding_model==embedding_model,literal_column('knowledge_chunks.embedding_vector').is_not(None)).order_by(distance).limit(40),{'query_vector':'['+','.join(str(float(v)) for v in query_embedding)+']'}).all()
                    semantic=[(cosine(query_embedding,c.embedding),c.id) for c,_ in rows]
                    for chunk,document in rows:by_id[chunk.id]=(chunk,document);scores.setdefault(chunk.id,0.0)
    for order,weight in [(exact,2.0),([key for _,key in sorted(lexical,reverse=True)],1.0),([key for score,key in sorted(semantic,reverse=True) if score>.15],1.0)]:
        for rank,key in enumerate(order,1):scores[key]=scores.get(key,0)+weight/(60+rank)
    results=[]
    for key,score in sorted(scores.items(),key=lambda entry:(-entry[1],entry[0])):
        if score<=0:continue
        chunk,document=by_id[key]
        # Recheck policy state from the authoritative table, not index metadata.
        if document.payload.get('source_type') in {'policy','policy_document'}:
            record=session.get(Policy,document.payload.get('policy_version'))
            if not record or record.status not in {'active','superseded'}:continue
        results.append({'citation':citation(chunk,document),'content':chunk.content,'score':score,'classification':document.classification,'external_approved':document.payload.get('external_approved',False),'document_id':document.id})
        if len(results)>=top_k:break
    return results

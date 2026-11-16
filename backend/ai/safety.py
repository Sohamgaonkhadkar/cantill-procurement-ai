"""Authorization and provenance checks run before any external client is created."""
from dataclasses import dataclass
import os,re,time
from fastapi import HTTPException
from ..workspace import isolated_demo
from ..db import User,AuthSession
from ..security import role_of

class PrivacyBoundaryError(ValueError): pass

@dataclass(frozen=True)
class ExternalContext:
    user_attested_fictional:bool=False
    classifications:tuple[str,...]=()
    sources_approved:bool=False

PRIVATE_IDENTIFIERS=re.compile(r'\b(?:ITM-\d+|RC-\d{4}-\d+|S\d{3,}|PUN\d+|CHK\d+)\b',re.I)
SECRET_PATTERN=re.compile(r'(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+\S+|postgres(?:ql)?(?:\+\w+)?://|-----BEGIN\s+\w*\s*PRIVATE KEY|(?:api[_ -]?key|password|secret)\s*(?::|=|is)\s*\S{8,})',re.I)

def assert_external_allowed(context,text=''):
    if not isolated_demo() or os.getenv('AI_EXTERNAL_CALLS_ENABLED','false').lower()!='true':
        raise PrivacyBoundaryError('External AI is disabled outside the isolated fictional demo')
    if not context.user_attested_fictional or not context.sources_approved:
        raise PrivacyBoundaryError('Explicit fictional-input acknowledgement and approved source provenance are required')
    if not context.classifications or any(kind not in {'fictional_demo','public_approved'} for kind in context.classifications):
        raise PrivacyBoundaryError('Private or unclassified context must remain local')
    if PRIVATE_IDENTIFIERS.search(text) or SECRET_PATTERN.search(text):
        raise PrivacyBoundaryError('Potential private identifiers or credentials must remain local')

def authorize_actor(session,actor):
    account=session.get(User,str(actor))
    if not account or account.payload.get('enabled',True) is False: raise HTTPException(401,'Sign in required')
    if account.role!=role_of(actor): raise HTTPException(403,'Account permissions changed; sign in again')
    if getattr(actor,'session_id',''):
        login=session.get(AuthSession,actor.session_id)
        if not login or login.revoked or login.expires_at<=int(time.time()): raise HTTPException(401,'Sign in required')
    return account

def safe_provider_error(error):
    # Never include SDK exception messages, request bodies, prompts or headers.
    return {'type':type(error).__name__,'status':getattr(error,'status_code',None) or getattr(getattr(error,'response',None),'status_code',None)}

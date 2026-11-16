"""Individual principals, salted password hashes, revocation and DB-backed throttles."""
import base64,hashlib,hmac,json,os,secrets,time
from uuid import uuid4
from functools import lru_cache
from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from .db import User,AuthSession,AuthThrottle,Audit,now as timestamp

SECRET=os.getenv('SESSION_SECRET') or secrets.token_hex(32)
DEMO=os.getenv('DEMO_MODE','true').lower()=='true'
ROLES={'requester','buyer','admin'}
SUBMISSION_PASSWORDS={role:f'corvo-{role}-demo' for role in sorted(ROLES)}

def submission_access():
    return os.getenv('SUBMISSION_ACCESS','false').lower()=='true'
if not DEMO and (not os.getenv('SESSION_SECRET') or any(not os.getenv(r.upper()+'_PASSWORD') for r in ROLES)):
    raise RuntimeError('Production requires SESSION_SECRET and all three role passwords')
_sessions=None

class Principal(str):
    def __new__(cls,user_id,role,session_id=''):
        obj=str.__new__(cls,user_id); obj.role=role; obj.session_id=session_id
        return obj

def configure_sessions(factory):
    global _sessions
    _sessions=factory

def role_of(actor): return getattr(actor,'role',str(actor))

def hash_password(password):
    salt=secrets.token_hex(16); iterations=600000
    value=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),iterations).hex()
    return f'pbkdf2_sha256${iterations}${salt}${value}'

def verify_password(password,stored):
    try:
        algorithm,iterations,salt,expected=stored.split('$')
        if algorithm!='pbkdf2_sha256' or not 100000<=int(iterations)<=2000000: return False
        actual=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(iterations)).hex()
        return hmac.compare_digest(actual,expected)
    except (ValueError,TypeError): return False

@lru_cache(maxsize=4)
def fallback_hash(name):
    password=os.getenv(name.upper()+'_PASSWORD','corvo-demo' if DEMO and name in ROLES else '')
    return hash_password(password or 'non-existent-account-no-login')

def authenticate(name,password):
    now=int(time.time()); name=name.lower().strip()
    failure=None; result=None
    with _sessions().begin() as s:
        # Atomic insertion and row locking make the throttle shared across
        # PostgreSQL function instances, including the first failed attempt.
        if s.bind.dialect.name=='postgresql':
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        key=hashlib.sha256(name.encode()).hexdigest()
        s.execute(insert(AuthThrottle).values(id=key,failures=0,window_started=now).on_conflict_do_nothing(index_elements=['id']))
        throttle=s.scalar(select(AuthThrottle).where(AuthThrottle.id==key).with_for_update())
        if now-throttle.window_started>=900: throttle.failures=0; throttle.window_started=now
        if throttle.failures>=5:
            failure=HTTPException(429,'Too many failed attempts; retry after the 15-minute window',headers={'Retry-After':str(max(1,900-(now-throttle.window_started)))})
        else:
            account=s.get(User,name)
            stored=account.payload.get('password_hash') if account else None
            if not stored: stored=fallback_hash(name if name in ROLES else '__missing__')
            usable_credential=bool(account and (account.payload.get('password_hash') or (name in ROLES and account.payload.get('type')=='controlled_demo_account')))
            valid=verify_password(password,stored) and usable_credential
            # Explicit public submission access uses published demo credentials,
            # never exposes or substitutes the private operational passwords.
            if submission_access() and name in ROLES and account and account.payload.get('type')=='controlled_demo_account':
                valid=valid or hmac.compare_digest(password.encode(),SUBMISSION_PASSWORDS[name].encode())
            if not account or account.payload.get('enabled',True) is False or not valid:
                throttle.failures+=1
                failure=HTTPException(401,'Invalid credentials')
            else:
                throttle.failures=0; throttle.window_started=now
                sid=secrets.token_urlsafe(32); expires=now+28800
                s.add(AuthSession(id=sid,user_id=account.id,expires_at=expires,revoked=False))
                payload=base64.urlsafe_b64encode(json.dumps({'sub':account.id,'sid':sid,'exp':expires},separators=(',',':')).encode()).decode()
                signature=hmac.new(SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
                result={'access_token':payload+'.'+signature,'token_type':'bearer','role':account.role,'user_id':account.id,'expires_in':28800}
        action='auth.login' if result else 'auth.throttled' if failure.status_code==429 else 'auth.failed'
        s.add(Audit(id=str(uuid4()),created_at=timestamp(),payload={'actor':name,'action':action,'details':{'role':result['role'] if result else None}}))
    # A raised exception inside the transaction would undo the failure counter.
    if failure: raise failure
    return result

bearer=HTTPBearer(auto_error=False)
def user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer)):
    try:
        token=credentials.credentials if credentials else ''
        if len(token)>4096: raise ValueError()
        payload,signature=token.split('.')
        expected=hmac.new(SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature,expected): raise ValueError()
        value=json.loads(base64.urlsafe_b64decode(payload)); now=int(time.time())
        if value['exp']<=now: raise ValueError()
        with _sessions()() as s:
            session=s.get(AuthSession,value['sid']); account=s.get(User,value['sub'])
            if not session or session.user_id!=value['sub'] or session.revoked or session.expires_at<=now or not account or account.payload.get('enabled',True) is False or account.role not in ROLES: raise ValueError()
            return Principal(account.id,account.role,session.id)
    except SQLAlchemyError: raise HTTPException(503,'Authentication storage temporarily unavailable',headers={'Retry-After':'5'})
    except Exception: raise HTTPException(401,'Sign in required',headers={'WWW-Authenticate':'Bearer'})

def require(actor,*roles):
    if role_of(actor) not in roles: raise HTTPException(403,'Role not permitted')

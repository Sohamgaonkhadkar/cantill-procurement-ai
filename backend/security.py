import base64,hashlib,hmac,json,os,secrets,time
from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials

SECRET=os.getenv('SESSION_SECRET') or secrets.token_hex(32)
DEMO=os.getenv('DEMO_MODE','true').lower()=='true'
ROLES={'requester','buyer','admin'}
if not DEMO and (not os.getenv('SESSION_SECRET') or any(not os.getenv(r.upper()+'_PASSWORD') for r in ROLES)):
    raise RuntimeError('Production requires SESSION_SECRET and all three role passwords')

def login(role,password):
    if role not in ROLES: raise HTTPException(401,'Invalid credentials')
    expected=os.getenv(role.upper()+'_PASSWORD','corvo-demo' if DEMO else '')
    if not expected or not hmac.compare_digest(password,expected): raise HTTPException(401,'Invalid credentials')
    payload=base64.urlsafe_b64encode(json.dumps({'role':role,'exp':int(time.time())+28800}).encode()).decode()
    sig=hmac.new(SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
    return payload+'.'+sig

bearer=HTTPBearer(auto_error=False)
def user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer)):
    try:
        token=credentials.credentials if credentials else ''; payload,sig=token.split('.')
        expected=hmac.new(SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,expected): raise ValueError()
        value=json.loads(base64.urlsafe_b64decode(payload))
        if value['exp']<time.time() or value['role'] not in ROLES: raise ValueError()
        return value['role']
    except Exception: raise HTTPException(401,'Sign in required')

def require(actor,*roles):
    if actor not in roles: raise HTTPException(403,'Role not permitted')

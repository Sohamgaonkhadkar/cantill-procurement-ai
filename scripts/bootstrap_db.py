"""Idempotent policy/demo-principal seeds. Contains no original task data."""
from sqlalchemy import text
from backend.db import connect,Policy,User
from backend.policy import initial_policy
def main():
    engine,Session=connect()
    with Session.begin() as s:
        if engine.dialect.name=='postgresql': s.execute(text('SELECT pg_advisory_xact_lock(246813579)'))
        if not s.get(Policy,'5.0'): s.add(Policy(id='5.0',status='active',payload=initial_policy()))
        for role in ['requester','buyer','admin']:
            if not s.get(User,role): s.add(User(id=role,role=role,payload={'type':'controlled_demo_account','name':role.title()}))
    engine.dispose()
    print('Policy and role bootstrap complete; no private kit data bundled')
if __name__=='__main__': main()

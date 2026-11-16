"""Idempotent policy/demo-principal seeds. Contains no original task data."""
from sqlalchemy import text,select
from backend.db import connect,Policy,User,Item
from backend.policy import initial_policy
from backend.workspace import isolated_demo,DEMO_PASSWORDS
def main():
    engine,Session=connect()
    with Session.begin() as s:
        if engine.dialect.name=='postgresql': s.execute(text('SELECT pg_advisory_xact_lock(246813579)'))
        if not s.get(Policy,'5.0'): s.add(Policy(id='5.0',status='active',payload=initial_policy()))
        for role in ['requester','buyer','admin']:
            if not s.get(User,role): s.add(User(id=role,role=role,payload={'type':'controlled_demo_account','name':role.title()}))
        if isolated_demo():
            from backend.security import hash_password
            from backend.demo import dataset,batch
            from backend.service import save_data,execute_run
            s.flush()
            for role,password in DEMO_PASSWORDS.items():
                s.get(User,role).payload={'type':'public_demo_role','name':'Demo '+role.title(),'password_hash':hash_password(password),'enabled':True,'access_scope':'evaluation'}
            if s.scalar(select(Item.id).limit(1)) is None:
                save_data(s,dataset())
                execute_run(s,batch(),'5.0','admin')
        # Explicit deployment-time local indexing, never a cold-start task and
        # never an external embedding call. Private PDFs are not auto-ingested.
        if __import__('os').getenv('RAG_ENABLED','false').lower()=='true':
            from backend.ai.knowledge import sync_core_sources
            sync_core_sources(s)
    engine.dispose()
    print('Policy and role bootstrap complete; no private kit data bundled')
if __name__=='__main__': main()

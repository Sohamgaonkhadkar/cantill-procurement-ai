"""Run from repository root: python -m scripts.import_kit /private/kit"""
import sys
from backend.ingest import load_kit
from backend.db import connect,Base,transaction_lock,CATALOG_LOCK,Commitment
from sqlalchemy import select
from backend.service import save_data,audit
engine,Session=connect()
Base.metadata.create_all(engine)
data=load_kit(sys.argv[1])
with Session.begin() as session:
    transaction_lock(session,CATALOG_LOCK,exclusive=True)
    if session.scalar(select(Commitment.id).limit(1)):
        raise RuntimeError('Cannot replace master data after commitments; use a separate database')
    snapshot=save_data(session,data)
    audit(session,'local-import','data.imported',{'snapshot':snapshot,'items':len(data.items),'contracts':len(data.contracts)})
print(f'Imported {len(data.items)} items, {len(data.contracts)} verified contracts; snapshot {snapshot[:12]}')

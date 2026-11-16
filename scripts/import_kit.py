"""Run from repository root: python -m scripts.import_kit /private/kit"""
import sys
from backend.ingest import load_kit
from backend.db import connect,Base
from backend.service import save_data,audit
engine,Session=connect()
Base.metadata.create_all(engine)
data=load_kit(sys.argv[1])
with Session.begin() as session:
    snapshot=save_data(session,data)
    audit(session,'local-import','data.imported',{'snapshot':snapshot,'items':len(data.items),'contracts':len(data.contracts)})
print(f'Imported {len(data.items)} items, {len(data.contracts)} verified contracts; snapshot {snapshot[:12]}')

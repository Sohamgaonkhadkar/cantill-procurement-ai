"""Isolated real FastAPI/SQLite server for browser tests; synthetic data only."""
import os,secrets
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.chdir(root)
os.environ['DATABASE_URL']='sqlite:///'+str(root/'.private'/('e2e-'+secrets.token_hex(5)+'.db'))
os.environ['DEMO_MODE']='true'
os.environ['SUBMISSION_ACCESS']='true'
os.environ.pop('VERCEL',None)
from backend import api
from backend.domain import Data
from backend.service import save_data
from backend.policy import initial_policy
from backend.db import Policy,User
from pypdf import PdfWriter
api.db.Base.metadata.create_all(api.engine)
items={code:{'item_code':code,'description':description,'uom':unit,'category':category,'item_type':'Material','standard_price':price} for code,description,unit,category,price in [('ITM-9001','Ball bearing 6205-2RS','NOS','Bearings','100'),('ITM-9002','Hydraulic hose 1/2 inch 2 wire','MTR','Hydraulics','200')]}
suppliers={sid:{'supplier_id':sid,'name':name,'city':'Synthetic City','status':'Active','categories':'Bearings;Hydraulics','on_time_pct':delivery,'quality_rating':'4'} for sid,name,delivery in [('S-TEST-A','Synthetic Alpha','92'),('S-TEST-B','Synthetic Beta','85')]}
data=Data(items=items,suppliers=suppliers,plants={'P-A':{'plant':'P-A','name':'Alpha plant'}},history=[{'po_number':'H-TEST-'+code,'po_date':'2026-10-01','supplier_id':'S-TEST-A','item_code':code,'quantity':'10','unit_price':item['standard_price'],'uom':item['uom'],'plant':'P-A','delivered_on_time':'True'} for code,item in items.items()],contracts=[{'contract_id':'C-TEST','supplier_id':'S-TEST-A','start_date':'2026-01-01','end_date':'2028-12-31','value_cap':'10000','consumed_value':'0','lines':[{'item_code':'ITM-9001','uom':'NOS','rate':'90'}]}])
with api.Session.begin() as s:
    s.add(Policy(id='5.0',status='active',payload=initial_policy()))
    for role in ['requester','buyer','admin']: s.add(User(id=role,role=role,payload={'type':'controlled_demo_account','name':role.title()}))
    s.flush();save_data(s,data)
asset=root/'.private/e2e-manual-contract.pdf'
writer=PdfWriter();writer.add_blank_page(width=600,height=800)
with asset.open('wb') as f:writer.write(f)
if __name__=='__main__':
    import uvicorn
    uvicorn.run(api.app,host='127.0.0.1',port=8002)

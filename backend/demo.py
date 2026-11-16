"""Explicit synthetic inputs for an isolated, non-persistent engine preview.

No result rows are stored here. Every preview is calculated by engine.process.
The assessment dataset, active policies and purchasing ledger are never used.
"""
from .domain import Data


def dataset():
    items={
        'DEMO-BEARING':{'description':'Demo ball bearing 6205-2RS','uom':'NOS','category':'Bearings','item_type':'Material','standard_price':'100'},
        'DEMO-GLOVES':{'description':'Demo nitrile safety gloves','uom':'PAIR','category':'Safety','item_type':'Material','standard_price':'50'},
        'DEMO-HOSE':{'description':'Demo hydraulic hose 1/2 inch','uom':'MTR','category':'Hydraulics','item_type':'Material','standard_price':'200'},
        'DEMO-PRESS':{'description':'Demo hydraulic press 10 ton','uom':'NOS','category':'Capital','item_type':'Capex','standard_price':'1500000'},
    }
    for code,item in items.items():item['item_code']=code
    suppliers={sid:{'supplier_id':sid,'name':name,'city':'Demo City','status':status,'categories':'Bearings;Safety;Hydraulics;Capital','on_time_pct':delivery,'quality_rating':quality} for sid,name,status,delivery,quality in [
        ('DEMO-S-A','Demo Industrial Supply','Active','93','4'),
        ('DEMO-S-B','Demo Engineering Partners','Active','96','4.5'),
        ('DEMO-S-BLOCKED','Demo Ineligible Supplier','Blocked','100','5'),
    ]}
    return Data(items=items,suppliers=suppliers,plants={'DEMO-PLANT':{'plant':'DEMO-PLANT','name':'Synthetic demonstration plant'}},
        history=[{'po_number':'DEMO-HISTORY-1','po_date':'2026-10-01','supplier_id':'DEMO-S-A','item_code':'DEMO-GLOVES','quantity':'100','unit_price':'45','uom':'PAIR','plant':'DEMO-PLANT','delivered_on_time':'True'}],
        contracts=[{'contract_id':'DEMO-CONTRACT-1','supplier_id':'DEMO-S-A','start_date':'2026-01-01','end_date':'2027-12-31','value_cap':'25000','consumed_value':'0','lines':[{'item_code':'DEMO-BEARING','uom':'NOS','rate':'80'}]}])


def batch():
    data=dataset()
    def row(pr,item,qty,created='2026-11-01 10:00',need='2026-11-20',urgency='Normal',**extra):
        master=data.items.get(item,{})
        return {'pr_no':pr,'pr_line':'1','created_at':created,'requester':'Synthetic demo requester','department':'Demonstration','plant':'DEMO-PLANT','item_code':item,'description':master.get('description','Demo laser inspection platform'),'quantity':qty,'uom':master.get('uom','NOS'),'estimated_unit_price':'','need_by_date':need,'urgency':urgency,**extra}
    return [row('DEMO-PR-01','DEMO-BEARING','10'),row('DEMO-PR-02','DEMO-BEARING','5'),
        row('DEMO-PR-03','DEMO-GLOVES','100'),row('DEMO-PR-04','DEMO-GLOVES','5000',need='2026-12-10',urgency='Emergency'),
        row('DEMO-PR-05','DEMO-HOSE','100'),row('DEMO-PR-06','DEMO-HOSE','6000',created='2026-11-20 10:00',need='2026-12-20'),
        row('DEMO-PR-07','DEMO-PRESS','1'),row('DEMO-PR-08','','2',estimated_unit_price='20000'),row('DEMO-PR-09','DEMO-GLOVES','0')]

from copy import deepcopy
import pytest
from backend.domain import Data
from backend.policy import initial_policy

@pytest.fixture
def data():
    return Data(items={'I-A':{'item_code':'I-A','description':'Ball bearing 6205-2RS','uom':'NOS','category':'Bearings','item_type':'Material','standard_price':'100'},'I-B':{'item_code':'I-B','description':'Hydraulic hose 1/2 inch 2 wire','uom':'MTR','category':'Hydraulics','item_type':'Material','standard_price':'200'},'I-C':{'item_code':'I-C','description':'Production press 10 ton','uom':'NOS','category':'Capital','item_type':'Capex','standard_price':'1000000'}},suppliers={'S-A':{'supplier_id':'S-A','name':'Alpha','status':'Active','categories':'Bearings;Hydraulics;Capital','on_time_pct':'90','quality_rating':'4'},'S-B':{'supplier_id':'S-B','name':'Beta','status':'Active','categories':'Bearings;Capital','on_time_pct':'80','quality_rating':'5'},'S-X':{'supplier_id':'S-X','name':'Blocked','status':'Blocked','categories':'Bearings','on_time_pct':'100','quality_rating':'5'}},plants={'P-A':{'plant':'P-A','name':'Alpha plant'},'P-B':{'plant':'P-B','name':'Beta plant'}},history=[{'po_number':'H-A','po_date':'2026-10-01','supplier_id':'S-A','item_code':'I-A','quantity':'10','unit_price':'100','uom':'NOS','plant':'P-A','delivered_on_time':'True'}],contracts=[])

@pytest.fixture
def policy(): return initial_policy()

def line(pr='PR-A',**changes):
    return {'pr_no':pr,'pr_line':'1','created_at':'2026-11-01 10:00','requester':'Synthetic user','department':'Testing','plant':'P-A','item_code':'I-A','description':'Ball bearing 6205-2RS','quantity':'10','uom':'NOS','estimated_unit_price':'','need_by_date':'2026-11-20','urgency':'Normal',**changes}

def contract(cid='C-A',**changes):
    return {'contract_id':cid,'supplier_id':'S-A','start_date':'2026-01-01','end_date':'2026-12-31','value_cap':'100000','consumed_value':'0','lines':[{'item_code':'I-A','uom':'NOS','rate':'90'}],**changes}

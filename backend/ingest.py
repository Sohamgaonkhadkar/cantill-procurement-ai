"""Private, idempotent kit import and reviewable contract extraction."""
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader
from pypdf.errors import PyPdfError
import re
from .domain import Data,read_csv,number,digest

def pdf_text(content):
    if not content.startswith(b'%PDF-'): raise ValueError('Expected a PDF file')
    try:
        reader=PdfReader(BytesIO(content))
        if len(reader.pages)>100: raise ValueError('PDF exceeds 100 pages')
        text='\n'.join(p.extract_text() or '' for p in reader.pages)
    except PyPdfError as exc: raise ValueError('Unreadable or encrypted PDF; provide an unlocked document') from exc
    if not text.strip(): raise ValueError('No extractable text; scanned PDFs require manual transcription')
    return text

def extract_contract(content):
    text=pdf_text(content)
    def capture(pattern):
        m=re.search(pattern,text,re.I|re.S)
        if not m: raise ValueError('Cannot extract contract field: '+pattern)
        return m.group(1)
    cid=capture(r'Contract No\.\s*(RC-\d{4}-\d+)')
    sid=capture(r'Supplier\s+ID\s+(S\d+)')
    start=capture(r'valid from\s+(\d{4}-\d{2}-\d{2})')
    end=capture(r'valid from\s+\d{4}-\d{2}-\d{2}\s+to\s+(\d{4}-\d{2}-\d{2})')
    cap=capture(r'not exceed INR\s+([\d,]+(?:\.\d+)?)')
    lines=[]
    for m in re.finditer(r'^\d+\s+(ITM-\d+)\s+(.+?)\s+([A-Z]{2,5})\s+([\d,]+(?:\.\d+)?)\s*$',text,re.M):
        code,desc,uom,rate=m.groups(); lines.append({'item_code':code,'description':desc,'uom':uom,'rate':str(number(rate))})
    if not lines: raise ValueError('No contract lines extracted; enter fields manually')
    return {'contract_id':cid,'supplier_id':sid,'start_date':start,'end_date':end,'value_cap':str(number(cap)),'consumed_value':'0','lines':lines,'provenance':{'type':'signed_pdf','sha256':digest(text),'extracted_text':text,'signature_verified':False}}

def _validate_contract(contract,data):
    from datetime import date
    if contract['supplier_id'] not in data.suppliers: raise ValueError('Unknown contract supplier')
    if date.fromisoformat(contract['start_date'])>date.fromisoformat(contract['end_date']): raise ValueError('Contract validity reversed')
    if number(contract['value_cap'])<=0 or number(contract['consumed_value'])<0: raise ValueError('Invalid contract ceiling')
    if number(contract['consumed_value'])>number(contract['value_cap']): raise ValueError('Consumption exceeds cap')
    seen=set()
    for line in contract['lines']:
        item=data.items.get(line['item_code'])
        if not item or item['uom']!=line['uom'] or number(line['rate'])<=0: raise ValueError('Unknown item, mismatched UoM or invalid contract rate')
        if line['item_code'] in seen: raise ValueError('Duplicate contract item')
        seen.add(line['item_code'])
    if not seen: raise ValueError('Contract requires lines')
    return contract

def validate_contract(contract,data):
    try: return _validate_contract(contract,data)
    except (KeyError,TypeError,AttributeError) as exc: raise ValueError('Contract requires complete dates, ceiling, supplier and item lines') from exc

def load_kit(root):
    root=Path(root)
    headers={'item_master.csv':['item_code','description','uom','category','item_type','standard_price'],
      'supplier_master.csv':['supplier_id','name','city','categories','status','on_time_pct','quality_rating'],
      'plants.csv':['plant','name'],
      'po_history.csv':['po_number','po_date','supplier_id','item_code','quantity','uom','unit_price','plant','delivered_on_time'],
      'contract_register.csv':['contract_id','supplier_id','start_date','end_date','value_cap','consumed_value'],
      'contract_lines.csv':['contract_id','item_code','description','uom','rate']}
    def read(path):
        try: rows=read_csv((root/path).read_bytes(),headers[Path(path).name])
        except FileNotFoundError as exc: raise ValueError('Missing required input '+path) from exc
        identity={'item_master.csv':['item_code'],'supplier_master.csv':['supplier_id'],'plants.csv':['plant'],'contract_register.csv':['contract_id'],'contract_lines.csv':['contract_id','item_code']}.get(Path(path).name)
        if identity:
            keys=[tuple(r[k] for k in identity) for r in rows]
            if any(not all(k) for k in keys) or len(set(keys))!=len(keys): raise ValueError('Empty or duplicate master identity in '+path)
        return rows
    data=Data({x['item_code']:x for x in read('master_data/item_master.csv')},{x['supplier_id']:x for x in read('master_data/supplier_master.csv')},{x['plant']:x for x in read('master_data/plants.csv')},read('master_data/po_history.csv'),[])
    lines=read('contracts/contract_lines.csv'); contracts={}
    for c in read('contracts/contract_register.csv'):
        c['lines']=[x for x in lines if x['contract_id']==c['contract_id']]; c['provenance']={'type':'register','baseline_date':'2026-10-31'}; contracts[c['contract_id']]=c
    for path in sorted((root/'contracts/pdf').glob('*.pdf')):
        extracted=extract_contract(path.read_bytes()); cid=extracted['contract_id']
        if cid in contracts:
            c=contracts[cid]
            for field in ['supplier_id','start_date','end_date']:
                if c[field]!=extracted[field]: raise ValueError(f'PDF/register conflict {cid} {field}')
            if number(c['value_cap'])!=number(extracted['value_cap']): raise ValueError('PDF/register cap conflict '+cid)
            old={l['item_code']:(l['uom'],number(l['rate'])) for l in c['lines']}; new={l['item_code']:(l['uom'],number(l['rate'])) for l in extracted['lines']}
            if old!=new: raise ValueError('PDF/register rate conflict '+cid)
            c['provenance']['pdf']=extracted['provenance']
        else: contracts[cid]=extracted
    data.contracts=[validate_contract(c,data) for c in contracts.values()]
    for i in data.items.values():
        if not i['item_code'] or not i['description'] or not i['uom'] or number(i['standard_price'])<=0: raise ValueError('Invalid item master record')
    for s in data.suppliers.values():
        if s['status'] not in {'Active','Inactive','Blocked'} or not 0<=number(s['on_time_pct'])<=100 or not 0<=number(s['quality_rating'])<=5: raise ValueError('Invalid supplier status or ratings')
    for h in data.history:
        if h['item_code'] not in data.items or h['supplier_id'] not in data.suppliers or h['plant'] not in data.plants: raise ValueError('Invalid history foreign key')
        if number(h['quantity'])<=0 or number(h['unit_price'])<=0: raise ValueError('Invalid historical quantity/price')
    return data

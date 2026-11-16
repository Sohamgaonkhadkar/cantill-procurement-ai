"""Transport-independent procurement domain and exact serialization."""
from dataclasses import dataclass, field
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, DefaultContext, getcontext
import csv, hashlib, io, json, re

# Set before FastAPI worker threads are created. Bounded numeric inputs and a
# 64-digit context keep multiplication/aggregation exact at the supported scale.
DefaultContext.prec=64
getcontext().prec=64

D = Decimal
OUTPUT_COLUMNS = ['pr_no','pr_line','resolved_item_code','group_id','po_id','decision','route','supplier_id','unit_price','group_value_inr','suggested_supplier_ids','policy_version','reason']
INPUT_COLUMNS = ['pr_no','pr_line','created_at','requester','department','plant','item_code','description','quantity','uom','estimated_unit_price','need_by_date','urgency']

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(',', ':')).encode()).hexdigest()

def money(value):
    return '' if value is None else format(D(value).quantize(D('.01'), rounding=ROUND_HALF_UP), '.2f')

def rate_text(value):
    """Preserve contractual rate precision; pad to at least two decimal places."""
    if value is None: return ''
    text=format(number(value),'f')
    if '.' not in text: return text+'.00'
    return text+'0'*max(0,2-len(text.split('.')[1]))

def number(value):
    raw=str(value).strip()
    if len(raw)>128: raise ValueError('Numeric input is too long')
    if ',' in raw and not re.fullmatch(r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d+)?',raw): raise ValueError('Malformed number grouping')
    try: result=D(raw.replace(',',''))
    except InvalidOperation as exc: raise ValueError('Invalid decimal number') from exc
    if not result.is_finite(): raise ValueError('Number must be finite')
    if abs(result)>D('1e18') or len(result.as_tuple().digits)>24 or result.as_tuple().exponent < -12:
        raise ValueError('Number exceeds supported precision or magnitude')
    return result

def read_csv(content: bytes, required=None):
    text = content.decode('utf-8-sig')
    if '\x00' in text: raise ValueError('CSV contains a NUL character')
    reader = csv.DictReader(io.StringIO(text, newline=''),strict=True)
    try: headers = reader.fieldnames or []
    except csv.Error as exc: raise ValueError('Malformed CSV header') from exc
    if len(headers) != len(set(headers)):
        raise ValueError('Duplicate CSV columns are not permitted')
    if any(not header.strip() for header in headers):
        raise ValueError('Blank CSV column names are not permitted')
    if required and (set(required) - set(reader.fieldnames or [])):
        raise ValueError('Missing CSV columns: ' + ', '.join(sorted(set(required)-set(reader.fieldnames or []))))
    rows=[]
    try:
        for row in reader:
            if len(rows)>=20000: raise ValueError('Maximum 20,000 rows per batch')
            rows.append(row)
    except csv.Error as exc: raise ValueError('Malformed CSV content or field exceeds supported length') from exc
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError('Malformed CSV row: column count mismatch')
    return [{k: v.strip() for k,v in r.items()} for r in rows]

def csv_bytes(rows, columns=OUTPUT_COLUMNS):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    for row in rows:
        # Text identifiers and names are untrusted too. Preserve strict numeric
        # cells, but neutralize spreadsheet formulas in every other column.
        numeric={'pr_line','quantity','estimated_unit_price','unit_price','group_value_inr','reference_price','rank','rate','value_cap','consumed_value','standard_price','quality_rating','on_time_pct'}
        def safe(key,value):
            text=str(value)
            if key in numeric and re.fullmatch(r'[+-]?\d+(?:\.\d+)?',text): return value
            return "'"+text if text.lstrip(' \t\r\n').startswith(('=','+','-','@')) else value
        writer.writerow({k:safe(k,v) for k,v in row.items()})
    return stream.getvalue().encode('utf-8')

@dataclass
class Data:
    items: dict
    suppliers: dict
    plants: dict
    history: list
    contracts: list

    def snapshot(self):
        contracts=deepcopy(self.contracts)
        for c in contracts: c['lines']=sorted(c['lines'],key=lambda x:x['item_code'])
        return dict(items=self.items,suppliers=self.suppliers,plants=self.plants,history=sorted(self.history,key=digest),contracts=sorted(contracts,key=lambda x:x['contract_id']))

@dataclass
class Line:
    raw: dict
    index: int
    item_code: str = 'NEW'
    item: dict = field(default_factory=dict)
    match: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    created: datetime | None = None
    need: date | None = None
    qty: Decimal = D(0)

@dataclass
class Requirement:
    id: str
    lines: list
    policy: dict

    @property
    def anchor(self): return self.lines[0]
    @property
    def quantity(self): return sum((x.qty for x in self.lines), D(0))
    @property
    def date(self): return self.anchor.created.date()

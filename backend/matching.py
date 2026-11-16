import re
from decimal import Decimal
from rapidfuzz.fuzz import token_set_ratio

def normalize(text):
    text=text.lower().replace('×','x').replace('"',' inch ')
    text=re.sub(r'(?<=\d)(?:inches|in)\b\.?',' inch',text)
    text=re.sub(r'\b(?:inches|in)\b\.?','inch',text)
    text=re.sub(r'(\d+)[ -]+(\d+)\s*/\s*([1-9]\d*)\s*inch\b',lambda m:format(Decimal(m[1])+Decimal(m[2])/Decimal(m[3]),'f')+' inch',text)
    text=re.sub(r'(\d+)\s*/\s*([1-9]\d*)\s*inch\b',lambda m:format(Decimal(m[1])/Decimal(m[2]),'f')+' inch',text)
    text=re.sub(r'(?<=\d)(?=inch\b)',' ',text)
    text=re.sub(r'(?<!\w)(\d+\.\d+)(?=\s*(?:inch|mm|cm|kg|kw|hp|sqmm)\b)',lambda m:format(Decimal(m[1]).normalize(),'f'),text)
    for a,b in {'brg':'bearing','pneu':'pneumatic','hyd':'hydraulic','assy':'assembly','ss':'stainless steel','ms':'mild steel','dia':'diameter','wldg':'welding','welding rod':'welding electrode'}.items():
        text=re.sub(r'\b'+a+r'\b',b,text)
    text=re.sub(r'\b(bearing|glove|cylinder|bolt|nut|washer|hose)s\b',r'\1',text)
    text=re.sub(r'\b(urgent|repeat|as per sample|for maintenance)\b',' ',text)
    text=re.sub(r'(?<=\d)\s*x\s*(?=\d)','x',text)
    text=re.sub(r'[^a-z0-9./]+',' ',text)
    text=re.sub(r'(?<=\d)\s+(?=(?:rs|zz|mm|kg|gb|kw|hp|sqmm)\b)','',text)
    return re.sub(r'\s+',' ',text).strip()

def specs(text):
    return re.findall(r'\d+(?:\.\d+)?',normalize(text))

def model_tokens(text):
    return {t for t in normalize(text).split() if re.search(r'[a-z]',t) and re.search(r'\d',t)}

def subsequence(a,b):
    it=iter(b)
    return all(any(x==y for y in it) for x in a)

def resolve(code,description,uom,items):
    if code:
        return (code,{'method':'code','confidence':1}) if code in items else ('NEW',{'method':'invalid_code','confidence':0,'error':'Unknown supplied item code'})
    query=normalize(description)
    if not query: return 'NEW',{'method':'empty','confidence':0,'error':'Description is required'}
    candidates=[]
    for key,item in items.items():
        target=normalize(item['description'])
        # Partial specifications remain candidates for clarification, never
        # evidence that a vaguely described catalog item is genuinely NEW.
        if not subsequence(specs(query),specs(target)): continue
        if not model_tokens(query)<=model_tokens(target): continue
        if uom and uom.upper()!=item['uom'].upper(): continue
        score=token_set_ratio(query,target)
        coverage=len(set(query.split())&set(target.split()))/max(1,len(set(target.split())))
        complete=specs(query)==specs(target) and coverage>=.6
        candidates.append((score,key,complete))
    candidates.sort(key=lambda x:(-x[0],x[1]))
    evidence={'method':'normalized_fuzzy','candidates':[{'item_code':k,'score':round(s,2),'specifications_complete':complete} for s,k,complete in candidates[:4]]}
    if candidates and candidates[0][2] and candidates[0][0]>=88 and (len(candidates)<2 or candidates[0][0]-candidates[1][0]>=7):
        return candidates[0][1],dict(evidence,confidence=candidates[0][0]/100)
    if candidates and candidates[0][0]>=65:
        return 'NEW',dict(evidence,confidence=0,error='Ambiguous or incomplete item match; select a master item explicitly')
    return 'NEW',dict(evidence,confidence=0)

import re
from rapidfuzz.fuzz import token_set_ratio

def normalize(text):
    text=text.lower().replace('×','x').replace('"',' inch ')
    for a,b in {'brg':'bearing','pneu':'pneumatic','hyd':'hydraulic','welding rod':'welding electrode'}.items():
        text=re.sub(r'\b'+a+r'\b',b,text)
    text=re.sub(r'\b(bearing|glove|cylinder|bolt|nut|washer|hose)s\b',r'\1',text)
    text=re.sub(r'\b(urgent|repeat|as per sample|for maintenance)\b',' ',text)
    text=re.sub(r'(?<=\d)\s*x\s*(?=\d)','x',text)
    return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9./]+',' ',text)).strip()

def specs(text):
    return re.findall(r'\d+(?:\.\d+)?',normalize(text))

def resolve(code,description,uom,items):
    if code:
        return (code,{'method':'code','confidence':1}) if code in items else ('NEW',{'method':'invalid_code','confidence':0,'error':'Unknown supplied item code'})
    query=normalize(description)
    if not query: return 'NEW',{'method':'empty','confidence':0,'error':'Description is required'}
    candidates=[]
    for key,item in items.items():
        target=normalize(item['description'])
        # Numeric specifications cannot be substituted by a fuzzy text score.
        if specs(query)!=specs(target): continue
        if uom and uom.upper()!=item['uom'].upper(): continue
        score=token_set_ratio(query,target)
        candidates.append((score,key))
    candidates.sort(key=lambda x:(-x[0],x[1]))
    evidence={'method':'normalized_fuzzy','candidates':[{'item_code':k,'score':round(s,2)} for s,k in candidates[:4]]}
    if candidates and candidates[0][0]>=88 and (len(candidates)<2 or candidates[0][0]-candidates[1][0]>=7):
        return candidates[0][1],dict(evidence,confidence=candidates[0][0]/100)
    if candidates and candidates[0][0]>=65:
        return 'NEW',dict(evidence,confidence=0,error='Ambiguous item match; select a master item explicitly')
    return 'NEW',dict(evidence,confidence=0)

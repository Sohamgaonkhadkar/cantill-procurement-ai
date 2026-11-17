"""Bounded cardinal grammar for literal intake quantities, not item dimensions."""
import re
from .domain import number

SMALL={w:i for i,w in enumerate('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split())}
TENS={w:10*(i+2) for i,w in enumerate('twenty thirty forty fifty sixty seventy eighty ninety'.split())}
WORDS=set(SMALL)|set(TENS)|{'hundred','thousand','lakh','lakhs','crore','crores','million','dozen','and','a'}

def cardinal(text):
    tokens=text.lower().replace('-',' ').split()
    total=0;part=0;last=None;scale=float('inf');seen=False
    for word in tokens:
        if word=='and':
            if not seen:raise ValueError('Invalid cardinal quantity')
            continue
        if word=='a':word='one'
        if word in SMALL or word in TENS:
            value=SMALL.get(word,TENS.get(word))
            if last is not None and (last<20 or last%10 or value>=10):raise ValueError('Invalid cardinal sequence')
            part+=value;last=value;seen=True
        elif word in {'hundred','dozen'}:
            if not seen or part<=0 or part>=100 or last is None:raise ValueError('Invalid quantity multiplier')
            part*=100 if word=='hundred' else 12;last=None
        elif word in {'thousand','lakh','lakhs','crore','crores','million'}:
            factor={'thousand':1000,'lakh':100000,'lakhs':100000,'crore':10000000,'crores':10000000,'million':1000000}[word]
            if not seen or part<=0 or factor>=scale:raise ValueError('Invalid cardinal scale')
            total+=part*factor;part=0;last=None;scale=factor
        else:raise ValueError('Unknown quantity word')
    if not seen:raise ValueError('No quantity evidence')
    return number(total+part)

def quantity_phrase(message):
    # Require an intake cue or an explicit unit; never scan arbitrary model text.
    pattern=r'\b(?:i\s+)?(?:need|get|quantity|qty|make\s+(?:that|it)|change\s+(?:quantity|qty)\s+to)\s+(?:(?:is|to)\s+)?([a-z]+(?:[ -]+[a-z]+)*)'
    match=re.search(pattern,message,re.I)
    if not match:return None
    tokens=match[1].lower().replace('-',' ').split();words=[]
    for token in tokens:
        if token not in WORDS:break
        words.append(token)
    return cardinal(' '.join(words)) if words else None

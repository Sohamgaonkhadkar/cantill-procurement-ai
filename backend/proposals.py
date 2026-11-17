"""Recognize a policy handoff; this never writes or interprets a policy."""
import re

def proposal_text(message):
    if re.search(r'\b(?:change|increase|reduce|revise|replace|set|amend|update)\b',message,re.I) and re.search(r'\b(?:policy|purchasing limit|spot limit|emergency limit|threshold|ranking weight|grouping window)\b',message,re.I):
        return message
    return None

def handoff(state,message,role):
    proposed=proposal_text(message)
    if not proposed:return None
    state={**state};state.pop('policy_proposal_text',None)
    if role!='admin':return state,'Policy proposals require an authorized Admin account. Your purchase draft is unchanged; no policy has been modified.'
    state['policy_proposal_text']=proposed
    return state,'I captured your exact proposed change. Open Review policy proposal to choose its base version and effective date, generate a draft diff and simulate it. Nothing has been approved or activated.'

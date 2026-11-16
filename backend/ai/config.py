from dataclasses import dataclass
from decimal import Decimal
import os

def flag(name,default=False):return os.getenv(name,str(default)).lower()=='true'
def bounded(name,default,minimum,maximum):
    try:return max(minimum,min(maximum,int(os.getenv(name,str(default)))))
    except ValueError:return default

@dataclass(frozen=True)
class Settings:
    enabled:bool
    rag_enabled:bool
    provider:str
    model:str
    embedding_model:str
    timeout:int
    max_tools:int
    max_iterations:int
    top_k:int
    max_input_chars:int
    max_output_tokens:int
    daily_token_limit:int
    daily_cost_limit:Decimal

def settings():
    try:cost=max(Decimal('0.01'),min(Decimal('1'),Decimal(os.getenv('CHAT_DAILY_COST_LIMIT_USD','0.25'))))
    except Exception:cost=Decimal('0.25')
    return Settings(flag('AI_CHAT_ENABLED'),flag('RAG_ENABLED'),os.getenv('LLM_PROVIDER','gemini'),os.getenv('LLM_MODEL','gemini-3.5-flash-lite'),os.getenv('EMBEDDING_MODEL','gemini-embedding-001'),bounded('CHAT_LLM_TIMEOUT_SECONDS',20,2,45),bounded('CHAT_MAX_TOOL_CALLS',4,1,6),bounded('CHAT_MAX_ITERATIONS',3,1,4),bounded('RAG_TOP_K',5,1,8),bounded('CHAT_MAX_INPUT_CHARS',16000,2000,24000),bounded('CHAT_MAX_OUTPUT_TOKENS',900,200,1600),bounded('CHAT_DAILY_TOKEN_LIMIT',200000,1000,500000),cost)

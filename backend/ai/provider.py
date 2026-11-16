"""Official SDK adapter. Privacy gates precede credentials, clients and calls."""
from dataclasses import dataclass
from decimal import Decimal
import json,os,time,math
from .config import settings,flag
from .safety import assert_external_allowed,safe_provider_error
from .budget import reserve,settle,failed

class ProviderUnavailable(ValueError):pass

@dataclass(frozen=True)
class ProviderResult:
    value:object
    model:str
    input_tokens:int
    output_tokens:int
    latency_ms:int

def credential():
    config=settings()
    # Gateway is intentionally unsupported: the owner selected direct Google
    # free-tier access, with no payment method or automatic paid fallback.
    return os.getenv('GEMINI_API_KEY') if config.provider=='gemini' else None

def rates(embedding=False):
    if settings().provider!='gemini':raise ProviderUnavailable('Only the configured direct Gemini provider is enabled')
    # Only documented free-tier IDs may be invoked. Quota errors never switch
    # models, providers or billing tiers. The key's Google project must remain
    # on the Free plan; the application cannot change its billing association.
    if (settings().embedding_model if embedding else settings().model) not in ({'gemini-embedding-001'} if embedding else {'gemini-3.5-flash-lite'}):raise ProviderUnavailable('Model is not on the reviewed free-tier allowlist')
    return Decimal(0),Decimal(0)

def throttle():
    from ..security import consume_rate_limit
    from fastapi import HTTPException
    from .config import bounded
    try:
        consume_rate_limit('gemini-workspace','ai.minute',bounded('GEMINI_REQUESTS_PER_MINUTE',8,1,15))
        consume_rate_limit('gemini-workspace','ai.day',bounded('GEMINI_REQUESTS_PER_DAY',100,1,250),86400)
    except HTTPException:raise ProviderUnavailable('Gemini request budget reached; local retrieval remains available') from None

def _strict_schema(schema):
    schema=json.loads(json.dumps(schema))
    def visit(value):
        if isinstance(value,dict):
            value.pop('default',None)
            if value.get('type')=='object' and 'properties' in value:
                value['additionalProperties']=False;value['required']=list(value['properties'])
            for child in list(value.values()):visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(schema);return schema

class Provider:
    def __init__(self,factory,actor):self.factory=factory;self.actor=actor

    def _client(self):
        from openai import OpenAI
        config=settings();key=credential()
        if not key:raise ProviderUnavailable('AI provider is not configured')
        if config.provider!='gemini':raise ProviderUnavailable('Unsupported configured provider')
        return OpenAI(api_key=key,base_url='https://generativelanguage.googleapis.com/v1beta/openai/',timeout=config.timeout,max_retries=0)

    def _chat_request(self,messages,context,**parameters):
        from .config import bounded
        config=settings();encoded=json.dumps(messages,ensure_ascii=False)
        assert_external_allowed(context,encoded)
        if not config.enabled:raise ProviderUnavailable('AI conversation is disabled')
        if len(encoded)>config.max_input_chars:raise ProviderUnavailable('AI context exceeds the configured input bound')
        if not credential():raise ProviderUnavailable('AI provider is not configured')
        input_rate,output_rate=rates()
        retries=bounded('CHAT_PROVIDER_RETRIES',1,0,1)
        for attempt in range(retries+1):
            # Each attempt rechecks privacy and authentication and reserves its
            # own quota. No transaction or mutation lock spans the SDK call.
            assert_external_allowed(context,encoded);throttle()
            usage_id=reserve(self.factory,self.actor,len(encoded.encode()),config.max_output_tokens,input_rate,output_rate,config.model)
            started=time.monotonic()
            try:
                with self._client() as client:
                    response=client.chat.completions.create(model=config.model,messages=messages,max_tokens=config.max_output_tokens,**parameters)
                usage=response.usage
                settle(self.factory,usage_id,usage.prompt_tokens if usage else len(encoded.encode()),usage.completion_tokens if usage else config.max_output_tokens,input_rate,output_rate,metadata={'latency_ms':int((time.monotonic()-started)*1000),'provider':config.provider,'attempt':attempt+1,'token_count_estimated':usage is None})
                return response
            except Exception as error:
                metadata=safe_provider_error(error);failed(self.factory,usage_id,metadata)
                if metadata['status'] in {500,502,503} and attempt<retries:
                    time.sleep(.25);continue
                raise ProviderUnavailable('Gemini is unavailable; continue using local procurement') from None
        raise ProviderUnavailable('Gemini is unavailable; continue using local procurement')

    def structured(self,messages,schema,context):
        started=time.monotonic()
        response=self._chat_request(messages,context,response_format={'type':'json_schema','json_schema':{'name':schema.__name__,'strict':True,'schema':_strict_schema(schema.model_json_schema())}})
        try:
            content=response.choices[0].message.content
            if not content:raise ValueError('No structured content')
            value=schema.model_validate_json(content)
            usage=response.usage
            return ProviderResult(value,response.model,usage.prompt_tokens if usage else 0,usage.completion_tokens if usage else 0,int((time.monotonic()-started)*1000))
        except (ValueError,IndexError,AttributeError):raise ProviderUnavailable('Gemini returned invalid structured content; continue locally') from None

    def tool_calls(self,messages,tools,context):
        response=self._chat_request(messages,context,tools=tools,tool_choice='auto',parallel_tool_calls=False)
        try:return [{'id':call.id,'name':call.function.name,'arguments':call.function.arguments} for call in (response.choices[0].message.tool_calls or [])][:settings().max_tools]
        except (ValueError,IndexError,AttributeError):raise ProviderUnavailable('Gemini returned invalid read-only tool calls; continue locally') from None

    def _embedding_request(self,texts,task_type):
        import httpx
        config=settings()
        model='models/'+config.embedding_model
        body={'requests':[{'model':model,'content':{'parts':[{'text':value}]},'outputDimensionality':1536,'taskType':task_type} for value in texts]}
        with httpx.Client(timeout=config.timeout,follow_redirects=False) as client:
            response=client.post('https://generativelanguage.googleapis.com/v1beta/'+model+':batchEmbedContents',headers={'x-goog-api-key':credential(),'Content-Type':'application/json'},json=body)
            response.raise_for_status()
            return response.json()

    def embed(self,texts,context,*,task_type='RETRIEVAL_DOCUMENT'):
        config=settings();encoded='\n'.join(texts)
        assert_external_allowed(context,encoded)
        if not flag('EXTERNAL_EMBEDDINGS_ENABLED') or len(texts)>16 or len(encoded)>config.max_input_chars:raise ProviderUnavailable('External embeddings are disabled or exceed bounds')
        if not credential():raise ProviderUnavailable('Embedding provider is not configured')
        if task_type not in {'RETRIEVAL_DOCUMENT','RETRIEVAL_QUERY'}:raise ProviderUnavailable('Unsupported embedding task')
        input_rate,_=rates(embedding=True);throttle()
        usage_id=reserve(self.factory,self.actor,len(encoded.encode()),0,input_rate,Decimal(0),config.embedding_model)
        try:
            # Native REST avoids OpenAI embedding response/encoding adapters.
            response=self._embedding_request(texts,task_type)
            vectors=[entry['values'] for entry in response['embeddings']]
            if len(vectors)!=len(texts) or any(len(v)!=1536 or any(not math.isfinite(n) for n in v) for v in vectors):raise ProviderUnavailable('Invalid embedding response')
            normalized=[]
            for vector in vectors:
                norm=math.sqrt(sum(v*v for v in vector))
                if norm<=0:raise ProviderUnavailable('Zero embedding vector')
                normalized.append([v/norm for v in vector])
            actual=response.get('usageMetadata',{}).get('promptTokenCount')
            estimated=actual is None
            settle(self.factory,usage_id,len(encoded.encode()) if estimated else actual,0,input_rate,Decimal(0),metadata={'provider':config.provider,'token_count_estimated':estimated})
            return normalized
        except Exception as error:
            failed(self.factory,usage_id,safe_provider_error(error));raise ProviderUnavailable('Embedding provider unavailable; local retrieval remains available') from None

def get_provider(factory,actor):return Provider(factory,actor)

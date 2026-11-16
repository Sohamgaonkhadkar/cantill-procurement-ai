"""Short, distributed reservations; never hold this transaction during a call."""
from datetime import datetime,timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from ..db import AIBudget,AIUsage,now
from .safety import authorize_actor
from .config import settings

class BudgetExceeded(ValueError):pass

def reserve(factory,actor,input_upper_bound,output_upper_bound,input_rate,output_rate,model):
    config=settings();reserved_cost=Decimal(input_upper_bound)*input_rate+Decimal(output_upper_bound)*output_rate
    token_count=input_upper_bound+output_upper_bound
    day=datetime.now(timezone.utc).date().isoformat()
    keys=['actor:'+str(actor)+':'+day,'workspace:'+day]
    usage_id=uuid4().hex
    with factory.begin() as session:
        authorize_actor(session,actor)
        if session.bind.dialect.name=='postgresql':from sqlalchemy.dialects.postgresql import insert
        else:from sqlalchemy.dialects.sqlite import insert
        for key in keys:
            session.execute(insert(AIBudget).values(id=key,tokens=0,cost_usd='0').on_conflict_do_nothing(index_elements=['id']))
            row=session.scalar(select(AIBudget).where(AIBudget.id==key).with_for_update())
            if row.tokens+token_count>config.daily_token_limit or Decimal(row.cost_usd)+reserved_cost>config.daily_cost_limit:
                raise BudgetExceeded('Daily AI budget reached; local procurement remains available')
            row.tokens+=token_count;row.cost_usd=str(Decimal(row.cost_usd)+reserved_cost)
        session.add(AIUsage(id=usage_id,actor=str(actor),created_at=now(),model=model,status='reserved',input_tokens=0,output_tokens=0,cost_usd=str(reserved_cost),payload={'budget_keys':keys,'reserved_tokens':token_count,'reserved_cost':str(reserved_cost)}))
    return usage_id

def settle(factory,usage_id,input_tokens,output_tokens,input_rate,output_rate,*,status='completed',metadata=None):
    actual=Decimal(input_tokens)*input_rate+Decimal(output_tokens)*output_rate
    with factory.begin() as session:
        usage=session.scalar(select(AIUsage).where(AIUsage.id==usage_id).with_for_update())
        if not usage or usage.status!='reserved':return
        for key in usage.payload['budget_keys']:
            row=session.scalar(select(AIBudget).where(AIBudget.id==key).with_for_update())
            row.tokens=max(0,row.tokens-usage.payload['reserved_tokens']+input_tokens+output_tokens)
            row.cost_usd=str(max(Decimal(0),Decimal(row.cost_usd)-Decimal(usage.payload['reserved_cost'])+actual))
        usage.input_tokens=input_tokens;usage.output_tokens=output_tokens;usage.cost_usd=str(actual);usage.status=status
        usage.payload={**usage.payload,**(metadata or {})}

def failed(factory,usage_id,metadata):
    # Keep the conservative reservation when a provider's usage is unknown.
    with factory.begin() as session:
        usage=session.get(AIUsage,usage_id)
        if usage:usage.status='provider_error';usage.payload={**usage.payload,**metadata}

from test_api import client
from backend.security import consume_rate_limit
from fastapi import HTTPException
import pytest

def test_operation_budget_persists_and_is_scoped_to_actor_and_operation(client):
    consume_rate_limit('alice','pdf-test',limit=2)
    consume_rate_limit('alice','pdf-test',limit=2)
    with pytest.raises(HTTPException) as exc:
        consume_rate_limit('alice','pdf-test',limit=2)
    assert exc.value.status_code==429 and int(exc.value.headers['Retry-After'])>0
    consume_rate_limit('bob','pdf-test',limit=2)
    consume_rate_limit('alice','chat-test',limit=2)
    assert client.get('/api/auth/me').status_code==200

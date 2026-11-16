import pytest
from backend.domain import read_csv, INPUT_COLUMNS, csv_bytes
from backend import api
from test_api import client
from conftest import line


@pytest.mark.parametrize('header',['a,a','a,'])
def test_duplicate_or_blank_csv_headers_are_rejected(header):
    with pytest.raises(ValueError):read_csv((header+'\n1,2\n').encode())


def test_duplicate_quantity_column_cannot_silently_overwrite_amount(client):
    raw=csv_bytes([line()],INPUT_COLUMNS).decode().splitlines()
    payload=raw[0]+',quantity\n'+raw[1]+',999999\n'
    response=client.post('/api/process-batch',files={'file':('duplicate.csv',payload,'text/csv')})
    assert response.status_code==422 and 'Duplicate CSV columns' in response.text
    assert client.get('/api/runs').json()['total']==0


def test_public_auth_openapi_documents_registration_throttle():
    paths=api.app.openapi()['paths']
    assert '429' in paths['/api/auth/register']['post']['responses']
    assert '401' not in paths['/api/auth/options']['get']['responses']

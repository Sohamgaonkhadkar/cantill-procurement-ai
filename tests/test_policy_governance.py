from test_api import client,upload

def test_uploaded_scoped_prose_goes_through_real_lifecycle(client):
    before=upload(client).json()
    response=client.post('/api/policies/upload-amendment',files={'file':('scoped.txt','If plant is P-A and category is Bearings and value exceeds INR 750 require RFQ','text/plain')},data={'version':'6.0','effective_date':'2026-04-01'})
    assert response.status_code==200,response.text
    assert response.json()['interpretation']['complete']
    result=client.post('/api/policies/6.0/simulate',json={'run_id':before['id']}).json()
    assert result['comparison']['affected_lines']==1
    for action in ['review','approve','activate']:
        response=client.post('/api/policies/6.0/'+action,json={'reason':'Verified plant/category clause and precedence'})
        assert response.status_code==200,response.text
    assert upload(client,version='6.0').json()['rows'][0]['route']=='RFQ'
    assert client.post('/api/runs/'+before['id']+'/replay').json()['matches']

def test_unparsed_source_cannot_be_silently_reviewed(client):
    response=client.post('/api/policies/propose-amendment',json={'text':'Unless special commercial circumstances apply, use the alternate route','version':'6.0','effective_date':'2026-04-01'})
    assert response.status_code==200
    assert not response.json()['interpretation']['complete']
    assert client.post('/api/policies/6.0/review',json={'reason':'Looks good without implementing the clause'}).status_code==409
    response=client.post('/api/policies/6.0/review',json={'reason':'Manually reconciled source with structured policy','manual_verification':True})
    assert response.status_code==200
    assert response.json()['governance']['manual_verification']

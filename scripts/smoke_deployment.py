"""Read-only checks plus an immutable batch run of explicitly supplied input.

Usage: CORVO_PASSWORD in environment; python -m scripts.smoke_deployment
  --base-url https://host --username evaluator --input /private/batch.csv
Never approves purchasing actions or changes policy/master records.
"""
import argparse
import hashlib
import os
from pathlib import Path
import httpx

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',required=True)
    parser.add_argument('--username',required=True)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--policy-version',default='5.0')
    args=parser.parse_args()
    password=os.environ.get('CORVO_PASSWORD')
    if not password: parser.error('Set CORVO_PASSWORD privately in the environment')
    raw=args.input.read_bytes()
    with httpx.Client(base_url=args.base_url.rstrip('/'),timeout=180) as client:
        def checked(response):
            if response.status_code>=400: raise RuntimeError(f'{response.request.method} {response.request.url.path}: HTTP {response.status_code}')
            return response
        assert checked(client.get('/health')).json()['status']=='ok'
        session=checked(client.post('/api/auth/login',json={'username':args.username,'password':password})).json()
        client.headers['Authorization']='Bearer '+session['access_token']
        try:
            checked(client.get('/api/auth/me'))
            checked(client.get('/api/master-data'))
            checked(client.get('/api/policies'))
            run=checked(client.post('/api/process-batch',files={'file':('assessment-input.csv',raw,'text/csv')},data={'policy_version':args.policy_version})).json()
            stored=checked(client.get('/api/runs/'+run['id'])).json()
            assert stored['output_hash']==run['output_hash']
            export=checked(client.get('/api/runs/'+run['id']+'/export.csv')).content
            replay=checked(client.post('/api/runs/'+run['id']+'/replay')).json()
            assert replay['matches']
            print({'health':'ok','authenticated':True,'rows':len(run['rows']),'requirements':len(run['requirements']),'issues':len(run['issues']),'output_hash':run['output_hash'],'csv_sha256':hashlib.sha256(export).hexdigest(),'replay_matches':True})
        finally:
            checked(client.post('/api/auth/logout'))
        assert client.get('/api/auth/me').status_code==401
        print('Logout revocation verified')

if __name__=='__main__': main()

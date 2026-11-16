"""Fail-closed configuration for the separately hosted public demonstration."""
import os
from urllib.parse import urlsplit,parse_qs

DEMO_ROLE='corvo_demo_app'
DEMO_SCHEMA='corvo_public_demo'
DEMO_PASSWORDS={role:'corvo-demo-'+role for role in ('admin','buyer','requester')}

def isolated_demo(url=None):
    if os.getenv('WORKSPACE_MODE','live')!='demo': return False
    parsed=urlsplit(url or os.getenv('DATABASE_URL',''))
    return (parsed.scheme in {'postgres','postgresql','postgresql+psycopg'}
        and parsed.username==DEMO_ROLE and bool(parsed.hostname)
        and '-pooler.' not in parsed.hostname
        and parse_qs(parsed.query).get('options')==['-csearch_path='+DEMO_SCHEMA])

def check_workspace_database(url):
    if os.getenv('WORKSPACE_MODE','live')=='demo' and not isolated_demo(url):
        raise RuntimeError('Public demo requires its restricted database role, direct endpoint and isolated schema')

def workspace_mode(): return 'demo' if isolated_demo() else 'live'

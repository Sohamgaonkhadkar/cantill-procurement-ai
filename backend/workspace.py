"""Fail-closed configuration for the separately hosted public demonstration."""
import os
import re
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

class WrongWorkspaceError(ValueError):pass

def assert_demo_rows(rows):
    """No persistence or financial processing of assessment rows in public demos."""
    from .demo import dataset
    data=dataset()
    for row in rows:
        if row.get('plant') not in data.plants or (row.get('item_code') and row['item_code'] not in data.items):
            raise WrongWorkspaceError('This is the DEMO WORKSPACE with fictional masters. Assessment batches are blocked here. Sign out and choose Individual account with your private evaluator credentials to process assessment data.')

def assert_demo_text(text):
    if re.search(r'\b(?:ITM-\d+|RC-\d{4}-\d+|S\d{3,}|PUN1|CHK1)\b',text,re.I):
        raise WrongWorkspaceError('Assessment identifiers cannot be stored in the public demo. Choose Individual account / private evaluator on the same login page.')

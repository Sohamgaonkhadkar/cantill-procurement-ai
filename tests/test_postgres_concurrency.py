from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import os
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from backend import api
from backend.db import ContractLedger
from backend.service import execute_run,save_data
from test_api import client
from conftest import line,contract

def test_independent_transactions_cannot_overspend_ceiling(client,data):
    if not os.getenv('TEST_DATABASE_URL'): pytest.skip('Requires dedicated PostgreSQL corvo_test database')
    data.contracts=[contract(value_cap='900')]
    with api.Session.begin() as s: save_data(s,data)
    with api.Session.begin() as s: first=execute_run(s,[line('PR-FIRST')],'5.0','admin')
    with api.Session.begin() as s: second=execute_run(s,[line('PR-SECOND')],'5.0','admin')
    barrier=Barrier(2)
    def approve(run):
        barrier.wait(timeout=10)
        try:
            # Deliberately bypass the process-local RLock. Only independent DB
            # transactions and PostgreSQL locks can protect this test.
            with api.Session.begin() as s: api.commit_requirement(s,run['id'],run['requirements'][0]['id'],'admin','Concurrent synthetic approval')
            return 200
        except HTTPException as exc: return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool: statuses=list(pool.map(approve,[first,second]))
    assert sorted(statuses)==[200,409]
    with api.Session() as s:
        assert sum(int(row.payload['amount']) for row in s.scalars(select(ContractLedger)))==900

def test_distinct_sourcing_votes_serialize_without_lost_approvals(client):
    if not os.getenv('TEST_DATABASE_URL'): pytest.skip('Requires dedicated PostgreSQL corvo_test database')
    from backend.db import Policy,SourcingRequest,RequirementRecord
    from backend.policy import initial_policy
    policy=initial_policy();policy['parameters']['additional_sourcing_approvals']={'Capex':1}
    with api.Session.begin() as s:
        s.get(Policy,'5.0').payload=policy
        run=execute_run(s,[line(item_code='I-C')],'5.0','admin')
    barrier=Barrier(2)
    def vote(actor):
        barrier.wait(timeout=10)
        with api.Session.begin() as s:
            return api.commit_requirement(s,run['id'],run['requirements'][0]['id'],actor,'Independent capex sourcing review')['status']
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(vote,['admin','buyer']))
    assert sorted(statuses)==['approved','awaiting_approval']
    with api.Session() as s:
        assert len(list(s.scalars(select(SourcingRequest))))==1
        record=s.scalar(select(RequirementRecord).where(RequirementRecord.run_id==run['id']))
        assert {v['actor'] for v in record.payload['approval_votes']}=={'admin','buyer'}

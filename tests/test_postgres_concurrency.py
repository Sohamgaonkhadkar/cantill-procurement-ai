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

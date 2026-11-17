"""A slow batch must not stop unrelated API requests from being served."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from backend import api
from test_api import client,upload

def test_health_remains_available_while_batch_database_work_is_waiting(client,monkeypatch):
    entered=Event();release=Event();original=api.execute_run
    def delayed(*args,**kwargs):
        entered.set()
        if not release.wait(10):raise RuntimeError('Test batch release was not signaled')
        return original(*args,**kwargs)
    monkeypatch.setattr(api,'execute_run',delayed)
    with ThreadPoolExecutor(max_workers=2) as workers:
        batch=workers.submit(upload,client)
        assert entered.wait(5),'Batch did not enter the controlled database wait'
        health=workers.submit(client.get,'/health')
        try:
            response=health.result(timeout=2)
            assert response.status_code==200 and response.json()['database']=='connected'
        finally:release.set()
        assert batch.result(timeout=10).status_code==200

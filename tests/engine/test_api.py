import os
import time

from fastapi.testclient import TestClient

from soma.api.app import create_app
from soma.validation import load_scenario


def test_planner(scenario, progress=None, cancel_event=None):
    """Spawn-picklable worker fixture; never selected from request data."""
    from soma.engine import plan_delivery
    progress('scheduling')
    time.sleep(0.15)
    return {'scenario': scenario, 'result': plan_delivery(scenario), 'details': {'worker_pid': os.getpid()}}


test_planner.__test__ = False


def slow_planner(scenario, progress=None, cancel_event=None):
    progress('horizon_preparation')
    time.sleep(30)


def finished(client, identifier):
    deadline = time.monotonic() + 30
    stages = set()
    while time.monotonic() < deadline:
        body = client.get(f'/plans/{identifier}').json()
        stages.add(body['stage'])
        if body['status'] in ('completed', 'failed', 'canceled'):
            return body, stages
        time.sleep(0.02)
    raise AssertionError('Job did not finish')


def test_jobs_process_isolation_immutable_result_and_download(tmp_path):
    scenario = load_scenario('fixtures/synthetic-relay/scenario.json')
    scenario['data_volume'] = {'value': 16, 'unit': 'byte'}
    with TestClient(create_app(planner=test_planner, temp_root=tmp_path)) as client:
        first = client.post('/plans', json=scenario)
        assert first.status_code == 202
        identifier = first.json()['job_id']
        job, stages = finished(client, identifier)
        assert job['status'] == 'completed', job
        assert job['worker_pid'] != os.getpid()
        assert job['scenario_sha256'] == first.json()['scenario_sha256']
        assert 'scheduling' in stages
        original = client.get(f'/plans/{identifier}').json()
        job['result']['warnings'].append('local mutation')
        assert client.get(f'/plans/{identifier}').json() == original
        second = client.post('/plans', json=scenario).json()['job_id']
        another, _ = finished(client, second)
        assert another['worker_pid'] != job['worker_pid']
        export = client.get(f'/plans/{identifier}/export')
        assert export.status_code == 200
        assert export.content == client.get(f'/plans/{identifier}/export').content
        assert client.get(f'/plans/{identifier}/summary').json()['scenario_sha256'] == first.json()['scenario_sha256']
        assert client.get('/plans/missing').status_code == 404


def test_cancel_queued_and_running_and_strict_json_limits(tmp_path):
    scenario = load_scenario('fixtures/synthetic-relay/scenario.json')
    with TestClient(create_app(planner=slow_planner, temp_root=tmp_path, max_workers=1, max_jobs=2)) as client:
        first = client.post('/plans', json=scenario).json()['job_id']
        deadline = time.monotonic() + 10
        while client.get(f'/plans/{first}').json()['status'] == 'queued' and time.monotonic() < deadline:
            time.sleep(0.02)
        second = client.post('/plans', json=scenario).json()['job_id']
        assert client.post('/plans', json=scenario).status_code == 429
        assert client.delete(f'/plans/{second}').json()['status'] == 'canceled'
        canceled = client.delete(f'/plans/{first}').json()
        assert canceled['status'] == 'canceled'
        assert canceled['result'] is None
        time.sleep(0.1)
        assert client.get(f'/plans/{first}').json()['status'] == 'canceled'
        assert client.get(f'/plans/{first}/export').status_code == 409
        assert client.post('/plans', content='{"a":1,"a":2}').status_code == 422
        assert client.post('/plans', content='{"a":NaN}').status_code == 422
        assert client.post('/plans', json={'scenario': scenario}).status_code == 422
        assert client.post('/plans', content=b' ' * 2_000_001).status_code == 413


def failed_planner(scenario, progress=None, cancel_event=None):
    raise RuntimeError('controlled worker failure')


def test_worker_failure_is_distinct_from_scientific_infeasibility(tmp_path):
    scenario = load_scenario('fixtures/synthetic-relay/scenario.json')
    with TestClient(create_app(planner=failed_planner, temp_root=tmp_path)) as client:
        identifier = client.post('/plans', json=scenario).json()['job_id']
        job, _ = finished(client, identifier)
        assert job['status'] == 'failed'
        assert job['result'] is None
        assert 'controlled worker failure' in job['error']
        assert client.get(f'/plans/{identifier}/export').status_code == 409


def test_production_planner_runs_fixture_and_exports_same_result(tmp_path):
    import hashlib
    import io
    import json
    import zipfile

    scenario = load_scenario('fixtures/synthetic-relay/scenario.json')
    scenario['data_volume'] = {'value': 16, 'unit': 'byte'}
    with TestClient(create_app(temp_root=tmp_path)) as client:
        submitted = client.post('/plans', json=scenario)
        assert submitted.status_code == 202, submitted.text
        identifier = submitted.json()['job_id']
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            job = client.get(f'/plans/{identifier}').json()
            if job['status'] in ('completed', 'failed', 'canceled'):
                break
            time.sleep(0.05)
        else:
            raise AssertionError('Production fixture did not finish within 40 seconds')
        assert job['status'] == 'completed', job
        assert job['result']['status'] == 'feasible_under_assumptions', job
        assert job['result']['delivered_bytes'] == 16
        assert job['worker_pid'] != os.getpid()
        package = client.get(f'/plans/{identifier}/export')
        assert package.status_code == 200
        with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
            assert json.loads(archive.read('scenario.json')) == scenario
            assert json.loads(archive.read('result.json')) == job['result']
            manifest = json.loads(archive.read('run-manifest.json'))
            assert manifest['scenario_sha256'] == submitted.json()['scenario_sha256']
            for name, record in manifest['files'].items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == record['sha256']
            assert 'replay.json' in archive.namelist()
            assert 'analysis-inputs.json' in archive.namelist()

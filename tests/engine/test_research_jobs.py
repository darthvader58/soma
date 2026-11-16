"""Durability, isolation and resource failures are separate from scientific results."""

import hashlib
import io
import json
import os
import sqlite3
import time
import zipfile

from fastapi import HTTPException
import pytest

from soma.api.research_jobs import ResearchJobStore, run_sync


def study():
    return {'study_version': '1.0.0', 'analysis_type': 'geometry', 'frame': 'MOON_ME_DE421',
            'reference_radius_m': 1737400, 'surface_model': 'reference_sphere',
            'sites': [{'id': 'custom', 'name': 'Custom site', 'latitude_deg': 3, 'longitude_deg_east': 7,
                       'elevation_m': 0, 'antenna_height_m': 2, 'panel_height_m': 1}],
            'time': {'start_utc': '2026-11-16T00:00:00Z', 'end_utc': '2026-11-16T00:02:00Z', 'step_s': 60},
            'spacecraft_refs': []}


def trusted_planner(request, *, data_root=None, progress=None, cancel_event=None):
    from soma.research import study_sha256
    progress({'stage': 'geometry'})
    return {'study_version': '1.0.0', 'study_sha256': study_sha256(request),
            'status': 'completed', 'request': request, 'worker_pid': os.getpid()}


def slow_planner(request, **kwargs):
    time.sleep(30)


def private_failure(request, **kwargs):
    raise ValueError('/private/secret-data/token=credential')


def wrong_hash_planner(request, **kwargs):
    return {'study_sha256': 'a' * 64, 'request': request, 'status': 'completed'}


def oversized_planner(request, **kwargs):
    result = trusted_planner(request, **kwargs)
    result['oversized'] = 'x' * 4_000_000
    return result


def finish(store, identifier, timeout=15):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        snapshot = store.snapshot(identifier)
        if snapshot['status'] in ('completed', 'failed', 'canceled'):
            return snapshot
        time.sleep(0.03)
    raise AssertionError('Research job did not finish')


def normalized():
    from soma.research import validate_study
    return validate_study(study())


def test_completed_job_and_exact_package_survive_restart(tmp_path):
    with_store = ResearchJobStore(tmp_path, planner=trusted_planner)
    try:
        submitted = with_store.submit(normalized())
        identifier = submitted['job_id']
        result = finish(with_store, identifier)
        assert result['status'] == 'completed', result
        assert result['worker_pid'] != os.getpid()
        assert result['result']['worker_pid'] == result['worker_pid']
        content, digest = with_store.package(identifier)
        assert digest == submitted['study_sha256']
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            assert json.loads(archive.read('study.json')) == normalized()
            assert json.loads(archive.read('result.json')) == result['result']
            manifest = json.loads(archive.read('run-manifest.json'))
            for name, record in manifest['files'].items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == record['sha256']
        result['result']['request']['sites'][0]['name'] = 'client mutation'
        assert with_store.snapshot(identifier)['result']['request'] == normalized()
    finally:
        with_store.close()
    reopened = ResearchJobStore(tmp_path, planner=trusted_planner)
    try:
        assert reopened.snapshot(identifier)['status'] == 'completed'
        assert reopened.package(identifier) == (content, digest)
        assert not list(tmp_path.glob('worker-*'))
    finally:
        reopened.close()


def test_restart_reconciles_unfinished_records_and_refuses_two_owners(tmp_path):
    first = ResearchJobStore(tmp_path, planner=slow_planner)
    try:
        with pytest.raises(RuntimeError, match='already has an owner'):
            ResearchJobStore(tmp_path, planner=trusted_planner)
        identifier = first.submit(normalized())['job_id']
    finally:
        first.close()
    with sqlite3.connect(tmp_path / 'jobs.sqlite3') as database:
        database.execute("UPDATE jobs SET status='running',stage='geometry' WHERE id=?", (identifier,))
    reopened = ResearchJobStore(tmp_path, planner=trusted_planner)
    try:
        snapshot = reopened.snapshot(identifier)
        assert snapshot['status'] == 'failed' and snapshot['stage'] == 'interrupted'
        assert snapshot['result'] is None
        assert 'restart' in snapshot['error']
        with pytest.raises(HTTPException) as error:
            reopened.package(identifier)
        assert error.value.status_code == 409
    finally:
        reopened.close()


def test_cancel_running_and_queued_and_retention_budget(tmp_path):
    store = ResearchJobStore(tmp_path, planner=slow_planner, max_workers=1, max_jobs=2)
    try:
        first = store.submit(normalized())['job_id']
        until = time.monotonic() + 5
        while store.snapshot(first)['status'] == 'queued' and time.monotonic() < until:
            time.sleep(.02)
        assert store.snapshot(first)['status'] == 'running'
        second = store.submit(normalized())['job_id']
        with pytest.raises(HTTPException) as error:
            store.submit(normalized())
        assert error.value.status_code == 429
        assert store.cancel(second)['status'] == 'canceled'
        assert store.cancel(first)['status'] == 'canceled'
        assert store.cancel(first)['status'] == 'canceled'
        assert not store.active
        assert not list(tmp_path.glob('worker-*'))
        assert store.snapshot(first)['result'] is None
        with pytest.raises(HTTPException) as error:
            store.snapshot('../../jobs.sqlite3')
        assert error.value.status_code == 404
    finally:
        store.close()


def test_timeout_and_private_worker_errors_are_not_scientific_outcomes(tmp_path):
    store = ResearchJobStore(tmp_path / 'timeout', planner=slow_planner, max_seconds=.2)
    try:
        identifier = store.submit(normalized())['job_id']
        result = finish(store, identifier)
        assert result['status'] == 'failed' and result['stage'] == 'timeout'
        assert result['result'] is None
    finally:
        store.close()
    for name, planner in [('private', private_failure), ('wrong-hash', wrong_hash_planner)]:
        store = ResearchJobStore(tmp_path / name, planner=planner)
        try:
            result = finish(store, store.submit(normalized())['job_id'])
            assert result['status'] == 'failed'
            assert result['result'] is None
            assert 'secret-data' not in json.dumps(result)
            assert 'credential' not in json.dumps(result)
        finally:
            store.close()


def test_sync_timeout_and_output_cap():
    with pytest.raises(HTTPException) as error:
        run_sync(normalized(), planner=slow_planner, timeout_s=.1)
    assert error.value.status_code == 504
    with pytest.raises(HTTPException) as error:
        run_sync(normalized(), planner=oversized_planner, timeout_s=10)
    assert error.value.status_code == 413


def test_sync_uses_no_multiprocessing_shared_memory(monkeypatch):
    import soma.api.research_jobs as jobs
    context = jobs.multiprocessing.get_context('spawn')

    def unsupported(*args, **kwargs):
        raise AssertionError('Hosted synchronous compute must not require /dev/shm')

    monkeypatch.setattr(context, 'Queue', unsupported)
    monkeypatch.setattr(context, 'Event', unsupported)
    monkeypatch.setattr(jobs.multiprocessing, 'get_context', lambda kind: context)
    result = json.loads(run_sync(normalized(), planner=trusted_planner, timeout_s=10))
    assert result['status'] == 'completed'


def test_expired_records_are_pruned_before_retention_rejection(tmp_path):
    store = ResearchJobStore(tmp_path, planner=trusted_planner, max_jobs=1, retention_seconds=1)
    try:
        first = store.submit(normalized())['job_id']
        assert finish(store, first)['status'] == 'completed'
        with store.lock:
            store.db.execute('UPDATE jobs SET updated=? WHERE id=?', (time.time() - 10, first))
            store.db.commit()
        assert store.submit(normalized())['job_id'] != first
        with pytest.raises(HTTPException) as error:
            store.snapshot(first)
        assert error.value.status_code == 404
    finally:
        store.close()


def thread_budget_planner(request, **kwargs):
    from soma.api.research_jobs import NUMERICAL_THREAD_VARIABLES
    result = trusted_planner(request, **kwargs)
    result['thread_environment'] = {name: os.environ.get(name) for name in NUMERICAL_THREAD_VARIABLES}
    return result


def test_spawn_overrides_inherited_native_thread_defaults(monkeypatch):
    from soma.api.research_jobs import NUMERICAL_THREAD_VARIABLES
    for name in NUMERICAL_THREAD_VARIABLES:
        monkeypatch.setenv(name, '32')
    result = json.loads(run_sync(normalized(), planner=thread_budget_planner, timeout_s=10))
    assert set(result['thread_environment'].values()) == {'1'}


def test_sync_interpreter_does_not_reenter_unguarded_server_main(tmp_path):
    import subprocess
    import sys
    marker = tmp_path / 'entered.txt'
    caller = tmp_path / 'server_bootstrap.py'
    caller.write_text(
        'from pathlib import Path\n'
        f'marker = Path({str(marker)!r})\n'
        "with marker.open('a') as stream: stream.write('entered\\n')\n"
        'from soma.api.research_jobs import run_sync\n'
        'from soma.research import validate_study\n'
        'from test_research_jobs import study, trusted_planner\n'
        'import json\n'
        "result = json.loads(run_sync(validate_study(study()), planner=trusted_planner, timeout_s=5))\n"
        "assert result['status'] == 'completed'\n")
    environment = os.environ.copy()
    environment['PYTHONPATH'] = os.pathsep.join(str(path or os.getcwd()) for path in sys.path)
    completed = subprocess.run([sys.executable, str(caller)], env=environment,
                               capture_output=True, text=True, timeout=10)
    assert completed.returncode == 0, completed.stderr
    assert marker.read_text().splitlines() == ['entered']

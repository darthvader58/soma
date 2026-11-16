"""Hosted bounds fail before numerical terrain preparation begins."""
import os
import sys
import time

import pytest

from soma.api.delivery import (_accepts_gzip, _stop_delivery_process,
                               scenario_template, validate_delivery_request)


def test_template_and_limits():
    request = validate_delivery_request({'scenario': scenario_template()})
    assert request['options']['chunk_bytes'] == 16777216
    assert request['scenario']['analysis_mode'] == 'terrain_ephemeris'


@pytest.mark.parametrize('accept,expected', [
    ('gzip', True), ('br, gzip;q=0', False), ('gzip;q=0, *;q=1', False),
    ('xgzip', False), ('*;q=.5', True), ('GZip;Q=0.7', True),
    ('gzip;q=nan', False), ('gzip;q=2', False), ('gzip;q=invalid', False),
])
def test_gzip_negotiation(accept, expected):
    assert _accepts_gzip(accept) is expected


@pytest.mark.parametrize('mutation', ['station_height', 'relay_span', 'modes', 'site', 'duration'])
def test_unsupported_provider_inputs_rejected_early(mutation):
    scenario = scenario_template()
    if mutation == 'station_height':
        scenario['profiles']['stations'][0]['height_m'] = -1
    elif mutation == 'relay_span':
        scenario['profiles']['relays'][0]['trajectory']['coverage']['end_utc'] = '2026-12-24T14:00:00Z'
    elif mutation == 'modes':
        scenario['profiles']['stations'][0]['terminals'][0]['mode_ids'].append('synthetic-uplink-2m')
    elif mutation == 'site':
        scenario['lander']['latitude_deg'] = -88
    else:
        scenario['analysis_horizon']['end_utc'] = '2026-11-25T14:00:00Z'
    with pytest.raises(ValueError):
        validate_delivery_request({'scenario': scenario})


@pytest.mark.skipif(os.name != 'posix', reason='POSIX process-group ownership')
def test_cleanup_kills_descendant_after_leader_exit(tmp_path):
    pidfile = tmp_path/'child.pid'
    code = ('import subprocess,sys; p=subprocess.Popen([sys.executable,"-c",'
            '"import time; time.sleep(120)"]); open(sys.argv[1],"w").write(str(p.pid))')
    from soma.api.processes import start_private_interpreter
    leader = start_private_interpreter([sys.executable, '-c', code, str(pidfile)], env=os.environ.copy())
    leader.wait(timeout=5)
    child_pid = int(pidfile.read_text())
    try:
        os.kill(child_pid, 0)
        _stop_delivery_process(leader)
        for _ in range(50):
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(.02)
        else:
            pytest.fail('Descendant survived completed-leader cleanup')
    finally:
        try:
            os.kill(child_pid, 9)
        except ProcessLookupError:
            pass


def test_router_transport_and_request_failures(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import soma.api.delivery as delivery
    app = FastAPI()
    app.include_router(delivery.delivery_router(data_root='/unused', capabilities_provider=lambda **kwargs: {
        'ready': True, 'persistence': 'none', 'async_available': False}))
    content = b'{"delivery_api_version":"1.0.0","test_payload":"' + b'x'*5000 + b'"}'
    monkeypatch.setattr(delivery, 'run_delivery_sync', lambda *args, **kwargs: content)
    with TestClient(app) as client:
        capability = client.get('/research/delivery/capabilities').json()
        assert capability['persistence'] == 'none' and capability['async_available'] is False
        response = client.post('/research/delivery/analyze', json={'scenario': scenario_template()},
                               headers={'Accept-Encoding': 'gzip;q=0, *;q=1'})
        assert response.status_code == 200 and response.content == content
        assert 'content-encoding' not in response.headers
        compressed = client.post('/research/delivery/analyze', json={'scenario': scenario_template()},
                                 headers={'Accept-Encoding': 'br, gzip;q=.5'})
        assert compressed.content == content and compressed.headers['content-encoding'] == 'gzip'
        assert compressed.headers['cache-control'] == 'private, no-store'
        assert client.post('/research/delivery/analyze', content=b'x'*128001).status_code == 413
        assert client.post('/research/delivery/analyze', content='{"scenario":{},"scenario":{}}').status_code == 422
        assert client.post('/research/delivery/analyze', content='{"scenario":NaN}').status_code == 422
        monkeypatch.setitem(delivery.LIMITS, 'max_response_wire_bytes', 500)
        assert client.post('/research/delivery/analyze', json={'scenario': scenario_template()},
                           headers={'Accept-Encoding': 'identity'}).status_code == 413


def slow_delivery(document, *, data_root):
    time.sleep(30)


def test_hard_deadline_stops_worker():
    from fastapi import HTTPException
    from soma.api.delivery import run_delivery_sync
    started = time.monotonic()
    with pytest.raises(HTTPException) as failure:
        run_delivery_sync({'scenario': scenario_template()}, data_root='/unused', runner=slow_delivery, timeout_s=.2)
    assert failure.value.status_code == 504
    assert time.monotonic()-started < 5


def test_delivery_worker_preloads_native_dependencies_before_calculation(tmp_path, monkeypatch):
    import json
    import soma.api.delivery as delivery
    sequence = []
    monkeypatch.setattr(delivery.sys, 'platform', 'test')
    monkeypatch.setattr(delivery, 'preload_hosted_libraries', lambda: sequence.append('preload'))

    def calculate(document, *, data_root):
        assert sequence == ['preload']
        sequence.append('calculate')
        return {'test': 'complete'}

    monkeypatch.setattr(delivery, 'calculate_delivery', calculate)
    control = tmp_path/'input.json'
    control.write_text(json.dumps({'document': {}, 'data_root': str(tmp_path)}))
    delivery._worker(control)
    assert sequence == ['preload', 'calculate']
    assert json.loads((tmp_path/'result.json').read_text()) == {'test': 'complete'}


@pytest.mark.skipif(sys.platform != 'darwin', reason='macOS native-safe launch path')
def test_macos_launch_uses_posix_spawn_from_threads(monkeypatch, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from soma.api.processes import start_private_interpreter, stop_private_interpreter
    import soma.api.processes as processes

    def forbidden_fork(*args, **kwargs):
        pytest.fail('macOS private worker must not call Popen/fork')

    monkeypatch.setattr(processes.subprocess, 'Popen', forbidden_fork)

    def launch(index):
        output = tmp_path/str(index)
        code = ('import os,pathlib,sys; '
                'assert os.getpid()==os.getsid(0)==os.getpgrp(); '
                'pathlib.Path(sys.argv[1]).write_text("fresh-session")')
        process = start_private_interpreter([sys.executable, '-c', code, str(output)], env=os.environ.copy())
        try:
            assert process.wait(timeout=5) == 0
            assert process.poll() == 0
            assert output.read_text() == 'fresh-session'
        finally:
            stop_private_interpreter(process)

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(launch, range(24)))

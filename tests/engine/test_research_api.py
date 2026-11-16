"""The hosted and persistent adapters share one validated scientific contract."""

import time

from fastapi.testclient import TestClient

from api.index import create_app as hosted_app
from soma.api.app import create_app
from test_research_jobs import private_failure, study, trusted_planner


def capabilities(**kwargs):
    return {'ready': True, 'frame': 'MOON_ME_DE421', 'coverage': {'start_utc': '2026-01-01T00:00:00Z',
            'end_utc': '2027-01-01T00:00:00Z'}, 'spacecraft': [], 'limitations': []}


def catalog():
    return {'catalog_version': 'test', 'frame': 'MOON_ME_DE421', 'reference_radius_m': 1737400,
            'sites': []}


def test_hosted_sync_does_new_calculation_with_no_fake_async_capability():
    with TestClient(hosted_app(research_planner=trusted_planner,
                    research_capabilities=capabilities, research_catalog=catalog)) as client:
        report = client.get('/api/research/capabilities').json()
        assert report['ready'] is True
        assert report['service_mode'] == 'serverless'
        assert report['async_available'] is False
        assert report['persistence']['kind'] == 'none'
        assert client.get('/api/research/catalog').json() == catalog()
        first = client.post('/api/research/analyze', json=study())
        assert first.status_code == 200, first.text
        changed = study()
        changed['sites'][0]['latitude_deg'] = 4
        second = client.post('/api/research/analyze', json=changed)
        assert second.status_code == 200, second.text
        assert first.json()['study_sha256'] != second.json()['study_sha256']
        assert first.headers['cache-control'] == 'private, no-store'
        assert client.post('/api/research/jobs', json=study()).status_code == 503
        assert client.get('/api/research/jobs/' + 'a' * 32).status_code == 503


def test_strict_request_limits_and_private_failure():
    with TestClient(hosted_app(research_planner=private_failure, research_catalog=catalog)) as client:
        assert client.post('/api/research/analyze', content='{"sites":[],"sites":[]}').status_code == 422
        assert client.post('/api/research/analyze', content='{"value":NaN}').status_code == 422
        assert client.post('/api/research/analyze', content=b'x' * 128_001).status_code == 413
        invalid = study()
        invalid['time']['start_utc'] = '2026-11-16T00:00:00'
        assert client.post('/api/research/analyze', json=invalid).status_code == 422
        response = client.post('/api/research/analyze', json=study())
        assert response.status_code == 503
        assert 'secret-data' not in response.text and 'credential' not in response.text


def test_persistent_routes_durable_export_and_explicit_cors(tmp_path, monkeypatch):
    monkeypatch.setenv('SOMA_RESEARCH_ALLOWED_ORIGINS', 'https://example.com')
    options = {'research_planner': trusted_planner, 'research_run_root': tmp_path / 'runs',
               'research_catalog': catalog, 'research_capabilities': capabilities, 'temp_root': tmp_path}
    with TestClient(create_app(**options)) as client:
        report = client.get('/research/capabilities').json()
        assert report['async_available'] is True
        assert report['persistence']['kind'] == 'sqlite_local_volume'
        assert client.get('/health').json()['research_async_available'] is True
        response = client.options('/research/jobs', headers={'Origin': 'https://example.com',
                         'Access-Control-Request-Method': 'POST'})
        assert response.headers['access-control-allow-origin'] == 'https://example.com'
        rejected = client.options('/research/jobs', headers={'Origin': 'https://other.example.com',
                         'Access-Control-Request-Method': 'POST'})
        assert 'access-control-allow-origin' not in rejected.headers
        submission = client.post('/research/jobs', json=study())
        assert submission.status_code == 202, submission.text
        identifier = submission.json()['job_id']
        until = time.monotonic() + 15
        while time.monotonic() < until:
            snapshot = client.get(f'/research/jobs/{identifier}').json()
            if snapshot['status'] in ('completed', 'failed'):
                break
            time.sleep(.03)
        assert snapshot['status'] == 'completed', snapshot
        package = client.get(f'/research/jobs/{identifier}/export')
        assert package.status_code == 200
        assert package.headers['x-soma-study-sha256'] == submission.json()['study_sha256']
        assert client.delete(f'/research/jobs/{identifier}').json()['status'] == 'completed'
    with TestClient(create_app(**options)) as reopened:
        assert reopened.get(f'/research/jobs/{identifier}').json() == snapshot
        assert reopened.get(f'/research/jobs/{identifier}/export').content == package.content


def test_unconfigured_local_service_does_not_advertise_persistence(tmp_path, monkeypatch):
    monkeypatch.delenv('SOMA_RESEARCH_RUN_ROOT', raising=False)
    with TestClient(create_app(temp_root=tmp_path, research_capabilities=capabilities)) as client:
        assert client.get('/research/capabilities').json()['async_available'] is False
        assert client.post('/research/jobs', json=study()).status_code == 503


def private_source_readiness(**kwargs):
    return {'ready': False, 'coverage': None, 'unavailable_reason': '/private/source/kernel.bsp',
            'spacecraft': [{'id': 'archived', 'available': False,
                            'unavailable_reason': '/home/worker/private-spk.bsp'}]}


def test_hosted_sources_remain_private_and_readiness_has_no_local_paths():
    with TestClient(hosted_app(research_capabilities=private_source_readiness)) as client:
        response = client.get('/api/research/capabilities')
        assert response.status_code == 200
        assert response.json()['ready'] is False
        assert '/private/' not in response.text and '/home/' not in response.text
        assert response.json()['async_available'] is False
        assert response.json()['persistence']['kind'] == 'none'
        assert client.get('/api/_data/de421.bsp').status_code == 404
        assert client.get('/api/research/data/de421.bsp').status_code == 404

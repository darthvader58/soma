"""Archive integrity and semantic replay are independent release checks."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from soma.exports import create_run_package
from soma.verification.exports import verify_run_package

ROOT=Path(__file__).resolve().parents[2]
RELAY=ROOT/'fixtures/phase-5/aligned-relay/run.zip'


def rewrite(member, transform, *, rehash=True):
    with zipfile.ZipFile(RELAY) as archive:
        files={name:archive.read(name) for name in archive.namelist()}
    files[member]=transform(files[member])
    if rehash:
        manifest=json.loads(files['run-manifest.json'])
        manifest['files'][member]={'sha256':hashlib.sha256(files[member]).hexdigest(),'size_bytes':len(files[member])}
        files['run-manifest.json']=json.dumps(manifest).encode()
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        for name, content in files.items():
            archive.writestr(name,content)
    return output.getvalue()


def test_exported_relay_replays_without_solver():
    report=verify_run_package(RELAY)
    assert report['passed'], report['errors']
    assert report['replay']['passed']
    assert report['replay']['delivered_bytes']==104857600


def test_legacy_direct_has_no_feasible_replay_claim():
    report=verify_run_package(ROOT/'fixtures/phase-4/synthetic-direct/run.zip')
    assert report['passed'], report['errors']
    assert report['replay'] is None
    assert 'no_feasible_schedule_claimed' in report['replay_status']
    assert 'legacy_nonfeasible' in report['display_status']


@pytest.mark.parametrize('member,old,new',[
    ('schedule.csv',b'2026-11-14T09:00:05Z',b'2026-11-14T09:00:06Z'),
    ('contacts.csv',b'256000',b'256001'),
    ('energy.csv',b',80\n',b',0\n'),
    ('buffer-history.csv',b'104857600',b'104857601'),
])
def test_rehashed_csv_corruption_fails_native_comparison(member,old,new):
    blob=rewrite(member,lambda content:content.replace(old,new,1))
    report=verify_run_package(blob)
    assert not report['passed']
    assert any(error['check']=='csv_native:'+member for error in report['errors'])


def test_unhashed_corruption_fails_manifest():
    report=verify_run_package(rewrite('energy.csv',lambda content:content+b'\n',rehash=False))
    assert not report['passed']
    assert any(error['check']=='checksum:energy.csv' for error in report['errors'])


def test_consistently_exported_false_feasible_schedule_fails_replay():
    run=json.loads((ROOT/'fixtures/phase-5/aligned-relay/run.json').read_text())
    # Re-export every derivative/checksum consistently after changing an endpoint
    # radio's service; optimizer is never called to diagnose this corruption.
    run['scenario']['profiles']['relays'][0]['service']['windows']=[]
    from soma.validation import scenario_sha256
    digest=scenario_sha256(run['scenario'])
    run['result']['scenario_sha256']=digest
    run['analysis_inputs']['scenario_sha256']=digest
    run['analysis_inputs']['environment']['scenario_sha256']=digest
    run['analysis_inputs']['environment']['scenario']=run['scenario']
    report=verify_run_package(create_run_package(run))
    assert not report['passed']
    assert any(error['check']=='independent_replay' for error in report['errors'])
    assert any(error['code']=='service_unavailable' for error in report['replay']['errors'])

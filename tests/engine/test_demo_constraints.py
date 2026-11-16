"""Physical mission controls preserve numerical inputs and honest unknown outcomes."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

from soma.schedule.replay import replay_schedule
from soma.validation import scenario_sha256
from soma.verification.exports import verify_run_package

ROOT = Path(__file__).resolve().parents[2]
CAPTURES = ROOT / 'fixtures/demo-constraints'


def physical_baseline():
    with zipfile.ZipFile(ROOT / 'fixtures/physical-south-pole/relay-later/run.zip') as archive:
        return {name:json.loads(archive.read(name+'.json')) for name in
                ('scenario','analysis-inputs','result','run-manifest')}


@pytest.mark.parametrize('name,code', [('battery-low','energy_reserve'), ('service-off','service_unavailable')])
def test_physical_constraint_capture_is_exact_and_verified(name, code):
    baseline = physical_baseline()
    expected = deepcopy(baseline['scenario'])
    if name == 'battery-low':
        expected['profiles']['hardware'][0]['battery']['initial_energy_wh'] = 11
    else:
        expected['profiles']['relays'][0]['service']['windows'] = []
    directory = CAPTURES / name
    run = json.loads((directory / 'run.json').read_text())
    assert run['scenario'] == expected
    assert run['scenario']['data_volume'] == {'unit':'MiB','value':16}
    analysis = deepcopy(baseline['analysis-inputs'])
    analysis['scenario_sha256'] = scenario_sha256(expected)
    analysis['environment']['scenario_sha256'] = scenario_sha256(expected)
    assert run['analysis_inputs'] == analysis
    assert not analysis['contacts_complete'] and analysis['generation_complete']
    assert all(bin['generation_w'] == 0 for bin in analysis['generation_bins'])
    assert run['details']['scheduler_options'] == baseline['run-manifest']['details']['scheduler_options']
    assert run['result']['status'] == 'unknown'
    assert run['result']['solver_status'] == 'unresolved'
    assert run['result']['model_fidelity'] == 'assumed_rate_simulation'
    assert run['result']['allocations'] == []
    assert run['result']['final_byte_arrival_utc'] is None
    assert run['result']['delivered_bytes'] is None
    assert run['validation'] is None
    summary = json.loads((directory / 'summary.json').read_text())
    assert summary['minimum_stored_energy_wh'] is None
    display = json.loads((directory / 'display-data.json').read_text())
    assert display['states'] == baseline['analysis-inputs']['states']
    assert display['states'] and display['renderer_states']
    assert verify_run_package(directory / 'run.zip')['passed']
    replay = replay_schedule(run['scenario'], analysis['contacts'], baseline['result']['allocations'], analysis['generation_bins'])
    assert not replay['passed']
    assert {error['code'] for error in replay['errors']} == {code}
    assert replay == json.loads((directory / 'baseline-counterfactual-replay.json').read_text())


def test_demo_source_and_artifact_checksums():
    report = json.loads((CAPTURES / 'demonstration.json').read_text())
    assert report['baseline_replay_passed']
    assert report['artifact_type'] == 'physical_mission_constraint_demonstration'
    for prefix in ('source','generator'):
        assert hashlib.sha256((ROOT / report[prefix+'_ref']).read_bytes()).hexdigest() == report[prefix+'_sha256']
    for case in report['cases']:
        for name,binding in case['files'].items():
            content = (CAPTURES / name).read_bytes()
            assert len(content) == binding['size_bytes']
            assert hashlib.sha256(content).hexdigest() == binding['sha256']


def test_generator_recomputes_both_physical_constraint_outcomes(tmp_path):
    spec = importlib.util.spec_from_file_location('demo_constraints', ROOT / 'scripts/build-demo-constraints.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.build(tmp_path)
    assert {case['case_id'] for case in report['cases']} == {'battery-low','service-off'}
    assert all(case['status'] == 'unknown' and case['export_verified'] for case in report['cases'])

"""Constraint captures preserve native inputs and independently expose the failure."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from soma.schedule.replay import replay_schedule
from soma.verification.exports import verify_run_package

ROOT = Path(__file__).resolve().parents[2]
CAPTURES = ROOT / 'fixtures/demo-constraints'


@pytest.mark.parametrize('name,code', [('battery-low', 'energy_reserve'), ('service-off', 'service_unavailable')])
def test_constraint_capture_is_exact_and_verified(name, code):
    source = json.loads((ROOT / 'fixtures/phase-6/sensitivity.json').read_text())
    archived = {row['case_id']:row for row in source['schedule_cases']}
    directory = CAPTURES / name
    run = json.loads((directory / 'run.json').read_text())
    assert run['scenario'] == archived[name]['scenario']
    assert run['analysis_inputs'] == archived[name]['analysis_inputs']
    assert run['details']['scheduler_options'] == archived[name]['settings']
    assert run['result']['status'] == 'infeasible_in_model'
    assert run['result']['solver_status'] == 'proven_infeasible_discretized_model'
    assert run['result']['model_fidelity'] == 'assumed_rate_simulation'
    assert run['result']['allocations'] == []
    assert run['result']['final_byte_arrival_utc'] is None
    assert run['validation'] is None
    summary = json.loads((directory / 'summary.json').read_text())
    assert summary['minimum_stored_energy_wh'] is None
    display = json.loads((directory / 'display-data.json').read_text())
    assert display['states'] == [] and display['renderer_states'] == []
    assert verify_run_package(directory / 'run.zip')['passed']
    replay = replay_schedule(run['scenario'], run['analysis_inputs']['contacts'],
        archived['baseline']['result']['allocations'], run['analysis_inputs']['generation_bins'])
    assert not replay['passed']
    assert {error['code'] for error in replay['errors']} == {code}
    assert replay == json.loads((directory / 'baseline-counterfactual-replay.json').read_text())


def test_demo_source_and_artifact_checksums():
    report = json.loads((CAPTURES / 'demonstration.json').read_text())
    assert report['baseline_replay_passed']
    for prefix in ('source', 'generator'):
        assert hashlib.sha256((ROOT / report[prefix+'_ref']).read_bytes()).hexdigest() == report[prefix+'_sha256']
    for case in report['cases']:
        for name, binding in case['files'].items():
            content = (CAPTURES / name).read_bytes()
            assert len(content) == binding['size_bytes']
            assert hashlib.sha256(content).hexdigest() == binding['sha256']


def test_generator_recomputes_both_constraint_outcomes(tmp_path):
    spec = importlib.util.spec_from_file_location('demo_constraints', ROOT / 'scripts/build-demo-constraints.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.build(tmp_path)
    assert {case['case_id'] for case in report['cases']} == {'battery-low', 'service-off'}
    assert all(case['status'] == 'infeasible_in_model' and case['export_verified'] for case in report['cases'])

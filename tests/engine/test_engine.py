"""End-to-end scientific conclusions require independent replay evidence."""
from copy import deepcopy

import pytest

from soma.engine import plan_run
from soma.preparation import prepare_analysis
from soma.validation import load_scenario


def small_scenario():
    scenario = load_scenario('fixtures/synthetic-relay/scenario.json')
    scenario['data_volume'] = {'value': 16, 'unit': 'byte'}
    return scenario


def test_direct_100mib_proven_infeasible_in_bounded_model():
    scenario = load_scenario('fixtures/synthetic-direct/scenario.json')
    run = plan_run(scenario)
    assert run['result']['status'] == 'infeasible_in_model'
    assert run['result']['solver_status'] == 'proven_infeasible_discretized_model'
    assert not run['result']['allocations']


def test_small_direct_delivery_passes_replay_and_preserves_assumptions():
    scenario = small_scenario()
    run = plan_run(scenario, options={'bin_s': 30, 'time_limit_s': 5})
    assert run['result']['status'] == 'feasible_under_assumptions'
    assert run['result']['model_fidelity'] == 'assumed_rate_simulation'
    assert run['result']['delivered_bytes'] == 16
    assert run['validation']['passed']
    assert run['validation']['final_byte_arrival_utc'] == run['result']['final_byte_arrival_utc']
    assert all(a['contact_id'].startswith('synthetic-direct') for a in run['result']['allocations'])
    assert 'synthetic' in ' '.join(run['result']['assumptions'] + run['result']['warnings']).lower()
    assert 'assumed' in ' '.join(run['result']['assumptions']).lower()
    assert not any('unresolved Phase 5 gate' in warning for warning in run['result']['warnings'])
    assert any('versioned renderer registration' in warning for warning in run['result']['warnings'])


@pytest.mark.parametrize('change', ['site', 'horizon'])
def test_unsupported_coverage_returns_unknown(change):
    scenario = small_scenario()
    if change == 'site':
        scenario['lander']['latitude_deg'] = -88.5
    else:
        scenario['analysis_horizon']['end_utc'] = '2026-11-14T10:04:00Z'
        scenario['deadline_utc'] = '2026-11-14T10:03:00Z'
    result = plan_run(scenario)['result']
    assert result['status'] == 'unknown'
    assert result['solver_status'] == 'unresolved'
    assert result['delivered_bytes'] is None
    assert not result['allocations']


def test_solver_timeout_and_incomplete_coverage_cannot_prove_infeasibility():
    scenario = small_scenario()
    result = plan_run(scenario, options={'time_limit_s': 0})['result']
    assert result['status'] == 'unknown'
    assert result['solver_status'] == 'unresolved'
    inputs = prepare_analysis(scenario)
    inputs['contacts_complete'] = False
    run = plan_run(scenario, analysis_inputs=inputs)
    assert run['result']['status'] == 'unknown'
    assert run['validation'] is None


def test_later_data_readiness_explains_the_effective_direct_capacity():
    scenario = load_scenario('fixtures/synthetic-direct/scenario.json')
    scenario['data_volume'] = {'value':16, 'unit':'MiB'}
    scenario['data_ready_utc'] = '2026-11-14T09:05:00Z'
    run = plan_run(scenario, options={'bin_s':30, 'time_limit_s':5})
    assert run['result']['status'] == 'infeasible_in_model'
    assert run['details']['limiting_bound']['available_bits'] == 76800000
    assert run['details']['limiting_bound']['required_bits'] == 134217728
    assert 'after data readiness' in run['result']['provenance']['reason']


def test_direct_capacity_bound_counts_receiver_delay_and_rounds_optimistically():
    from soma.engine import _direct_capacity_upper_bound
    scenario = load_scenario('fixtures/synthetic-direct/scenario.json')
    scenario['data_ready_utc'] = '2026-11-14T10:04:00Z'
    contact = {
        'sender':scenario['lander']['id'], 'receiver':scenario['station_refs'][0],
        'source_transmit_window':{'start_utc':'2026-11-14T10:00:00Z','end_utc':'2026-11-14T10:05:00Z'},
        'payload_rate_bps':1.1, 'available_capacity_bits':100,
        'one_way_delay':{'seconds':1.5},
    }
    assert _direct_capacity_upper_bound(scenario,[contact]) == 65
    contact['one_way_delay']['seconds'] = 61
    assert _direct_capacity_upper_bound(scenario,[contact]) == 0


def test_corrupted_optimizer_candidate_is_not_released(monkeypatch):
    from soma.schedule import optimizer

    scenario = small_scenario()
    valid = plan_run(scenario, options={'bin_s': 30, 'time_limit_s': 5})
    assert valid['result']['status'] == 'feasible_under_assumptions'
    allocations = deepcopy(valid['result']['allocations'])
    allocations[0]['byte_length'] += 1
    monkeypatch.setattr(optimizer, 'solve_schedule', lambda *args, **kwargs: {
        'solver_status': 'proven_optimum', 'allocations': allocations,
        'assumptions': [], 'warnings': [], 'details': {},
    })
    run = plan_run(scenario)
    assert not run['validation']['passed']
    assert run['result']['status'] == 'unknown'
    assert run['result']['solver_status'] == 'unresolved'
    assert not run['result']['allocations']
    assert any('replay' in warning.lower() for warning in run['result']['warnings'])

"""Physical requests retain finite resources and explicit coverage boundaries."""
from copy import deepcopy

import pytest

from soma.validation import ScenarioValidationError, load_scenario, validate_scenario


def test_physical_presets_preserve_controlled_task_and_deadline_rule():
    a = load_scenario('fixtures/physical-south-pole/scenario.json')
    b = load_scenario('fixtures/physical-south-pole/scenario-later.json')
    from soma.time import parse_utc
    for key in ('lander', 'data_volume', 'hardware_profile_ref', 'station_refs',
                'relay_refs', 'route_families', 'rate_method', 'pointing_assumption'):
        assert a[key] == b[key]
    assert a['profiles']['hardware'][0]['battery'] == b['profiles']['hardware'][0]['battery']
    for s in (a, b):
        assert (parse_utc(s['deadline_utc'])-parse_utc(s['data_ready_utc'])).total_seconds() == 21600
        for p in [*s['profiles']['hardware'], *s['profiles']['stations'], *s['profiles']['relays']]:
            assert p['service']['windows'] == [s['analysis_horizon']]
            assert p['storage_capacity_bytes'] > 0


@pytest.mark.parametrize('change', ['dataset', 'date', 'site', 'duration', 'relay', 'units'])
def test_unsupported_physical_requests_fail_explicitly(change):
    s = load_scenario('fixtures/physical-south-pole/scenario.json')
    if change == 'dataset':
        s['dataset_manifest_ref'] = 'synthetic-contract-v1'
    elif change == 'date':
        s['analysis_horizon']['start_utc'] = '2026-10-31T23:59:00Z'
        s['analysis_horizon']['end_utc'] = '2026-11-01T01:00:00Z'
        s['data_ready_utc'], s['deadline_utc'] = s['analysis_horizon'].values()
    elif change == 'site':
        s['lander']['latitude_deg'] = -85
    elif change == 'duration':
        s['analysis_horizon']['end_utc'] = '2026-11-24T15:00:00Z'
    elif change == 'relay':
        s['profiles']['relays'][0]['trajectory']['reference'] = 'unprovided_operational_ephemeris'
    else:
        s['profiles']['relays'][0]['trajectory']['position_unit'] = 'km'
    with pytest.raises(ScenarioValidationError):
        validate_scenario(s)


def _partial_analysis_case():
    from soma.preparation import prepare_analysis
    from soma.validation import scenario_sha256
    s = load_scenario('fixtures/synthetic-relay/scenario.json')
    s['data_volume'] = {'value':16,'unit':'byte'}
    inputs = prepare_analysis(s)
    s.update(analysis_mode='terrain_ephemeris', dataset_manifest_ref='physical-lola-de421-v1')
    s['profiles']['relays'][0]['trajectory'].update(kind='synthetic_two_body_lunar_preset', reference='soma-polar-200km-v1')
    inputs['scenario_sha256'] = scenario_sha256(s)
    inputs['environment']['scenario_sha256'] = scenario_sha256(s)
    inputs['contacts_complete'] = False
    for contact in inputs['contacts']:
        contact['one_way_delay'] = {'model':'constant_assumed','seconds':1.5}
    return s, inputs


def test_known_contacts_can_establish_feasibility_without_claiming_full_optimality():
    from soma.engine import plan_run
    s, inputs = _partial_analysis_case()
    run = plan_run(s, analysis_inputs=inputs, options={'bin_s':30,'time_limit_s':5})
    assert run['result']['status'] == 'feasible_under_assumptions'
    assert run['result']['solver_status'] == 'feasible_incumbent'
    assert run['validation']['passed']
    assert any('Unknown opportunities were excluded' in w for w in run['result']['warnings'])


def test_unknown_alternative_contacts_prevent_an_infeasibility_claim():
    from soma.engine import plan_run
    s, inputs = _partial_analysis_case()
    s['profiles']['hardware'][0]['battery']['initial_energy_wh'] = 10
    from soma.validation import scenario_sha256
    inputs['scenario_sha256'] = scenario_sha256(s)
    run = plan_run(s, analysis_inputs=inputs, options={'bin_s':30,'time_limit_s':5})
    assert run['result']['status'] == 'unknown'
    assert run['result']['solver_status'] == 'unresolved'
    assert run['result']['allocations'] == []
    assert 'unknown opportunities' in run['result']['provenance']['reason']


def test_state_batch_retains_strict_time_and_unit_validation():
    from soma.validation import validate_documents
    state = {'target':'relay','origin':'MOON','frame':'MOON_ME_DE421',
        'epoch':'2026-11-24T08:00:00Z','epoch_format':'rfc3339','time_scale':'UTC',
        'position':[1,2,3],'position_unit':'m','provenance_label':'synthetic test'}
    validate_documents([state,deepcopy(state)],'state')
    bad=deepcopy(state)
    bad['epoch']='2026-11-24T08:00:00'
    with pytest.raises(ScenarioValidationError):
        validate_documents([state,bad],'state')


@pytest.mark.parametrize('body', ['SUN', 'EARTH'])
@pytest.mark.parametrize('node', ['lander', 'relay', 'station'])
def test_body_names_cannot_replace_physical_illumination_states(body, node, monkeypatch):
    from soma.engine import plan_run
    import soma.preparation

    scenario = load_scenario('fixtures/physical-south-pole/scenario.json')
    if node == 'lander':
        scenario['lander']['id'] = body
    else:
        group, references = ('relays', 'relay_refs') if node == 'relay' else ('stations', 'station_refs')
        original = scenario['profiles'][group][0]['id']
        scenario['profiles'][group][0]['id'] = body
        scenario[references] = [body if value == original else value for value in scenario[references]]

    def must_not_prepare(*args, **kwargs):
        pytest.fail('A reserved body identifier reached scientific preparation')

    monkeypatch.setattr(soma.preparation, 'prepare_analysis', must_not_prepare)
    with pytest.raises(ScenarioValidationError, match='reserved for celestial-body states'):
        plan_run(scenario)

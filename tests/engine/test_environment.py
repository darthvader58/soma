"""Phase 3 artifacts preserve scientific identity and do not claim delivery."""

from copy import deepcopy
import pytest

from soma.environment import environment_diagnostic, synthetic_environment_fixture, GENERATION_MODEL
from soma.validation import load_json, scenario_sha256, validate_document


def example(family='synthetic-relay'):
    return synthetic_environment_fixture(load_json(f'fixtures/{family}/scenario.json'), load_json(f'fixtures/{family}/contacts.json'))


def test_synthetic_diagnostic_is_engine_generated_without_a_selected_schedule():
    report = example()
    values = [sample['visible_fraction'] for sample in report['solar_samples']]
    assert values[0] == 0 and values[-1] == 1
    assert any(0 < value < 1 for value in values)
    assert report['scenario_sha256'] == scenario_sha256(report['scenario'])
    assert 'allocations' not in report and 'delivered_bytes' not in report and 'solver_status' not in report
    assert report['battery']['status'] == 'satisfied_under_piecewise_constant_assumptions'
    assert all(row['electrical_load_w'] == 5 for row in report['battery']['intervals'])
    assert report['provenance']['input_class'] == 'synthetic'
    assert report['horizons']['antenna']['site']['height_m'] == 2
    assert report['horizons']['panel']['site']['height_m'] == 1
    assert {track['target'] for track in report['tracks'] if track['observer_role'] == 'panel'} >= {'SUN', 'EARTH', 'synthetic-earth-station'}
    assert len(report['contacts']) == 3
    assert not any(c['contact_id'] in ('synthetic-blocked-interval', 'synthetic-unknown-interval') for c in report['contacts'])
    for contact in report['contacts']:
        validate_document(contact, 'contact')
        assert contact['rate_method'] == 'assumed_net_rate'


def test_measured_terrain_unknowns_propagate_to_power_and_battery():
    geometry = load_json('soma/docs/phase-2/geometry-diagnostic.json')
    report = environment_diagnostic(geometry, generation_time_model=GENERATION_MODEL)
    assert all(sample['visible_fraction'] is None for sample in report['solar_samples'])
    assert all(sample['generated_power_w'] is None for sample in report['power_samples'])
    assert report['battery']['status'] == 'unknown'
    assert all(sample['stored_energy_wh'] is None for sample in report['battery']['samples'][1:])
    assert report['contacts'] == []
    assert report['contact_decisions'] and all(d['status'] == 'unknown' for d in report['contact_decisions'])


@pytest.mark.parametrize('corruption', ['hash', 'units', 'height', 'state_epoch', 'track_epochs'])
def test_geometry_identity_cannot_silently_drift(corruption):
    geometry = deepcopy(load_json('soma/docs/phase-2/geometry-diagnostic.json'))
    if corruption == 'hash':
        geometry['scenario_sha256'] = '0'*64
    elif corruption == 'units':
        geometry['tracks'][0]['samples'][0]['state']['position_unit'] = 'km'
    elif corruption == 'height':
        geometry['horizons']['panel']['site']['height_m'] = 100
    elif corruption == 'state_epoch':
        geometry['tracks'][0]['samples'][0]['state']['epoch'] = '2026-11-14T09:00:00Z'
    else:
        geometry['tracks'][1]['samples'].pop()
    with pytest.raises(ValueError):
        environment_diagnostic(geometry, generation_time_model=GENERATION_MODEL)


def test_temporal_generation_assumption_must_be_explicit():
    with pytest.raises(ValueError, match='explicitly'):
        environment_diagnostic({}, generation_time_model='continuous_bound')

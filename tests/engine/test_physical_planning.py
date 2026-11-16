"""Physical-input boundary checks independent of the route optimizer."""
from types import SimpleNamespace

import numpy as np
import pytest

from soma.physical import _shell_intervals, finite_terrain_test, prepare_physical_analysis


@pytest.mark.parametrize('alternative', ['terminal','mode'])
def test_ambiguous_radio_alternatives_are_rejected_instead_of_silently_discarded(alternative):
    from copy import deepcopy
    from soma.physical import _terminal_pairs
    sender = {'terminals':[{'id':'high-power','band':'X','mode_ids':['net-rate']} ]}
    receiver = {'terminals':[{'id':'rx','band':'X','mode_ids':['net-rate']} ]}
    if alternative == 'terminal':
        sender['terminals'].append({**sender['terminals'][0],'id':'low-power'})
    else:
        sender['terminals'][0]['mode_ids'].append('second-mode')
        receiver['terminals'][0]['mode_ids'].append('second-mode')
    with pytest.raises(ValueError,match='multiple radio'):
        _terminal_pairs(sender,receiver)


class SphereDEM:
    reference_radius_m = 1737400.0

    def __init__(self, missing=False, ridge_after_longitude=None):
        self.missing = missing
        self.ridge_after_longitude = ridge_after_longitude
        self.queries = []

    def sample(self, lat, lon):
        self.queries.append((lat, lon))
        elevation = 0.0
        if self.missing:
            elevation = None
        elif self.ridge_after_longitude is not None and lon > self.ridge_after_longitude:
            elevation = 10000.0
        return SimpleNamespace(elevation_m=elevation, quality_flags=())


def test_finite_endpoint_does_not_consult_ridge_beyond_spacecraft():
    radius = SphereDEM.reference_radius_m
    dem = SphereDEM(ridge_after_longitude=.01)
    start = np.array([radius+10, 0, 0])
    target = np.array([radius+100, 100, 0])
    outcome = finite_terrain_test(dem, start, target)
    assert outcome['status'] == 'clear'
    assert max(lon for lat, lon in dem.queries) < .01
    assert outcome['tested_range_m'] == pytest.approx(np.linalg.norm(target-start))


def test_missing_terrain_never_yields_clear_long_segment():
    radius = SphereDEM.reference_radius_m
    result = finite_terrain_test(SphereDEM(missing=True), [radius+10, 0, 0], [380000000, 0, 0])
    assert result['status'] == 'unknown'
    assert result['reason'] == 'missing_terrain_or_unresolved_clearance'


def test_long_segment_uses_only_low_altitude_samples():
    radius = SphereDEM.reference_radius_m
    dem = SphereDEM()
    result = finite_terrain_test(dem, [radius+10,0,0], [380000000,0,0])
    assert result['status'] == 'clear'
    assert len(dem.queries) < 2200
    assert result['tested_range_m'] > 300000000


def test_moon_body_blocks_without_sampling_dem():
    radius = SphereDEM.reference_radius_m
    dem = SphereDEM()
    result = finite_terrain_test(dem, [radius+10,0,0], [-radius-200000,0,0])
    assert result['status'] == 'blocked'
    assert dem.queries == []


def test_shell_intervals_are_clipped_to_finite_segment():
    assert _shell_intervals(np.array([2.,0,0]),np.array([3.,0,0]),1) == []
    assert _shell_intervals(np.array([0.,0,0]),np.array([2.,0,0]),1) == [(0,.5)]


def test_physical_input_rejects_unbounded_horizon_before_data_access():
    scenario = {'analysis_mode':'terrain_ephemeris','dataset_manifest_ref':'physical-lola-de421-v1',
                'analysis_horizon':{'start_utc':'2026-11-14T00:00:00Z','end_utc':'2026-11-15T00:00:00Z'}}
    with pytest.raises(ValueError,match='six hours'):
        prepare_physical_analysis(scenario)


def test_real_pinned_pipeline_preserves_input_identity_and_native_states():
    import os
    from pathlib import Path
    from soma.validation import load_json, load_scenario, scenario_sha256, validate_document

    root = Path(__file__).resolve().parents[2]
    data_root = Path(os.environ.get('SOMA_DATA_ROOT','/private/tmp/soma-phase2-data'))
    manifest = load_json(root/'data/de421-phase2.manifest.json')
    if any(not (data_root/k['path']).is_file() for k in manifest['kernels']):
        pytest.skip('Pinned external DE421 kernels are not acquired locally')
    model=load_json(root/'data/physical-first-release.manifest.json')
    for key in ('near_manifest_ref','far_manifest_ref','polar_manifest_ref'):
        if key in model:
            terrain_manifest=load_json(root/'data'/model[key])
            if any(not (data_root/f['path']).is_file() for f in terrain_manifest['files']):
                pytest.skip('Pinned external numerical LOLA grids are not fully acquired locally')
    scenario = load_scenario(root/'fixtures/physical-south-pole/scenario.json')
    identity = scenario_sha256(scenario)
    analysis = prepare_physical_analysis(scenario)
    assert analysis['scenario_sha256'] == identity == scenario_sha256(scenario)
    assert analysis['environment']['scenario_sha256'] == identity
    assert analysis['environment']['analysis_point']['latitude_deg'] == scenario['lander']['latitude_deg']
    assert analysis['contacts']
    assert analysis['generation_complete']
    assert all(g['generation_w'] is not None and g['generation_w'] >= 0 for g in analysis['generation_bins'])
    assert any(c['receiver'] in scenario['station_refs'] and c['sender'] == scenario['lander']['id'] for c in analysis['contacts'])
    for contact in analysis['contacts']:
        validate_document(contact,'contact')
        assert contact['rate_method'] == 'assumed_net_rate'
        assert contact['one_way_delay']['seconds'] > 0
        assert 'link_budget_not_computed' in contact['quality_flags']
    assert len(analysis['states']) > 1
    for state in analysis['states']:
        validate_document(state,'state')
        assert state['frame'] == 'MOON_ME_DE421'
        assert state['provenance_label'] == 'synthetic_two_body_lunar_preset'
    assert analysis['states'][0]['position'] != analysis['states'][-1]['position']
    assert analysis['environment']['geometry_events']
    assert all(e['boundary_uncertainty_s'] <= 2 for e in analysis['environment']['geometry_events'])


def test_station_elevation_uses_earth_surface_normal_not_moon_center_vector():
    from soma.physical import _station_elevation

    geometry = SimpleNamespace(spice=SimpleNamespace(pxform=lambda *args: np.eye(3)),_epoch=lambda epoch: 0)
    station = {'latitude_deg':45,'longitude_deg_east':0,'height_m':0}
    receiver = np.array([380000000.,1000.,0])
    normal = np.array([2**-.5,0,2**-.5])
    assert _station_elevation(geometry,station,receiver+1000*normal,receiver,'epoch') == pytest.approx(90)
    assert _station_elevation(geometry,station,receiver-1000*normal,receiver,'epoch') == pytest.approx(-90)

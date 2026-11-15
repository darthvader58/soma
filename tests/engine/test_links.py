"""Synthetic gate cases; no spacecraft or service prediction."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from soma.links import assess_contact
from soma.validation import validate_document

ROOT = Path(__file__).resolve().parents[2]


def inputs():
    scenario = json.loads((ROOT/'fixtures/synthetic-relay/scenario.json').read_text())
    contact = json.loads((ROOT/'fixtures/synthetic-relay/contacts.json').read_text())[0]
    candidate = {**contact, 'geometry_status': 'clear_under_sampling',
                 'geometry_reason': 'synthetic_clear_interval',
                 'geometry_evidence': {'method': 'synthetic_interval_not_actual_geometry', 'scope': 'interval_wide', 'coverage': deepcopy(contact['source_transmit_window'])},
                 'pointing_assumption': 'ideal_pointing', 'input_class': 'synthetic',
                 'service_assumption_label': 'SYNTHETIC declared service'}
    return candidate, scenario['profiles']['hardware'][0], scenario['profiles']['stations'][0]


def assess(c, a, b):
    return assess_contact(c, a, b, guard_s=0)


def test_assumed_rate_capacity_and_schema():
    result = assess(*inputs())
    contact = result['contacts'][0]
    validate_document(contact, "contact")
    assert contact['available_capacity_bits'] == 307200000
    assert result['model_fidelity'] == 'assumed_rate_simulation'
    assert 'link_budget_not_computed' in contact['quality_flags']
    assert result['endpoint_occupancy'][0]['available_capacity_bytes'] == 38400000


@pytest.mark.parametrize('change,reason', [('band', 'incompatible_band'), ('mode_ids', 'incompatible_mode')])
def test_wrong_radio(change, reason):
    c, a, b = inputs()
    b['terminals'][0][change] = 'other' if change == 'band' else ['other']
    result = assess(c, a, b)
    assert result['contacts'] == []
    assert result['decision']['reasons'] == [reason]


@pytest.mark.parametrize('status,decision', [('blocked','rejected'), ('unknown','unknown')])
def test_geometry_gate(status, decision):
    c, a, b = inputs()
    c['geometry_status'] = status
    result = assess(c, a, b)
    assert result['decision']['status'] == decision
    assert not result['contacts']


def test_arrival_service_and_both_endpoint_setup():
    c, a, b = inputs()
    c['one_way_delay'] = {'model': 'constant_assumed', 'seconds': 10}
    a['service']['windows'] = [deepcopy(c['source_transmit_window'])]
    b['service']['windows'] = [{'start_utc':'2026-11-14T08:50:20Z','end_utc':'2026-11-14T09:10:05Z'}]
    a['terminals'][0].update(acquisition_s=5, teardown_s=8)
    b['terminals'][0].update(acquisition_s=7, teardown_s=9)
    result = assess(c, a, b)
    contact = result['contacts'][0]
    assert contact['source_transmit_window'] == {'start_utc':'2026-11-14T08:50:17Z','end_utc':'2026-11-14T09:09:46Z'}
    occupied = result['endpoint_occupancy'][0]
    assert occupied['receiver_occupancy_interval'] == b['service']['windows'][0]
    assert occupied['sender_occupancy_interval'] == {'start_utc':'2026-11-14T08:50:12Z','end_utc':'2026-11-14T09:09:54Z'}


def test_delay_can_remove_service_entirely():
    c, a, b = inputs()
    c['one_way_delay'] = {'model':'constant_assumed', 'seconds':1800}
    result = assess(c, a, b)
    assert not result['contacts']
    assert result['decision']['status'] == 'rejected'


def test_missing_terminal_field_does_not_default_to_zero():
    c, a, b = inputs()
    del a['terminals'][0]['acquisition_s']
    assert assess(c, a, b)['decision']['status'] == 'unknown'


def test_budget_request_does_not_fall_back_to_assumed_rate():
    c, a, b = inputs()
    c['rate_method'] = 'link_budget'
    result = assess(c, a, b)
    assert result['decision']['status'] == 'unknown'
    assert not result['contacts']


def test_overlapping_service_windows_do_not_duplicate_capacity():
    c, a, b = inputs()
    b['service']['windows'].append(deepcopy(b['service']['windows'][0]))
    result = assess(c, a, b)
    assert len(result['contacts']) == 1
    assert result['contacts'][0]['available_capacity_bits'] == 307200000


def test_guards_trim_geometric_edges_once():
    c, a, b = inputs()
    result = assess_contact(c,a,b,guard_s=1)
    assert result['contacts'][0]['available_capacity_bits'] == 1198*256000


def test_missing_pointing_is_unknown():
    c, a, b = inputs()
    del c['pointing_assumption']
    assert assess(c, a, b)['decision']['status'] == 'unknown'


def geometry_inputs(height=2):
    from soma.geometry import surface_position
    from soma.terrain import SyntheticDEM
    from soma.terrain.dem import FRAME, RADIUS_M
    state = {'origin':'MOON', 'frame':FRAME, 'epoch':'2026-11-14T08:50:00Z',
             'epoch_format':'rfc3339', 'time_scale':'UTC', 'position_unit':'m',
             'position':list(surface_position(0,0,RADIUS_M,height))}
    target = {**state, 'position':list(surface_position(0,0.005,RADIUS_M,30))}
    return SyntheticDEM(lambda lat,lon: 100 if 0.01 < lon < 0.02 else 0,
                        identifier='beyond-relay-ridge'), state, target


def test_geometry_helper_limits_segment_and_labels_sample_scope():
    from soma.links import evaluate_geometry
    from soma.terrain.dem import RADIUS_M
    result = evaluate_geometry(*geometry_inputs(), step_m=2, clearance_m=0.1,
                               body_radius_m=RADIUS_M, occulting_spheres=[])
    assert result['status'] == 'clear'
    assert result['scope'] == 'single_same_epoch_sample_not_interval'


def test_geometry_helper_refuses_grazing_and_mismatched_epochs():
    from soma.links import evaluate_geometry
    from soma.terrain.dem import RADIUS_M
    dem, a, b = geometry_inputs(0)
    args = dict(step_m=2,clearance_m=0.1,body_radius_m=RADIUS_M,occulting_spheres=[])
    assert evaluate_geometry(dem,a,b,**args)['status'] == 'unknown'
    b['epoch'] = '2026-11-14T08:51:00Z'
    with pytest.raises(ValueError,match='epoch'):
        evaluate_geometry(dem,a,b,**args)


def test_station_normal_is_explicit_and_elevation_is_gated():
    from soma.links import evaluate_geometry
    from soma.terrain.dem import RADIUS_M
    dem, a, b = geometry_inputs()
    result = evaluate_geometry(dem,a,b,step_m=2,clearance_m=0.1,
        body_radius_m=RADIUS_M,occulting_spheres=[],station_normal=[1,0,0],minimum_elevation_deg=10)
    assert result['reason'] == 'station_below_minimum_elevation'


def test_geometry_setup_and_teardown_also_need_visibility():
    c,a,b = inputs()
    a['terminals'][0].update(acquisition_s=5, teardown_s=8)
    b['terminals'][0].update(acquisition_s=7, teardown_s=9)
    result = assess(c,a,b)
    assert result['contacts'][0]['source_transmit_window'] == {
        'start_utc':'2026-11-14T08:50:07Z', 'end_utc':'2026-11-14T09:09:51Z'}


def test_single_clear_sample_cannot_establish_interval_capacity():
    c, a, b = inputs()
    c['geometry_evidence']['scope'] = 'single_same_epoch_sample_not_interval'
    assert assess(c, a, b)['contacts'] == []
    c['geometry_evidence']['scope'] = 'interval_wide'
    c['geometry_evidence']['coverage']['start_utc'] = '2026-11-14T09:00:00Z'
    assert assess(c, a, b)['decision']['reasons'] == ['geometry_evidence_does_not_cover_candidate']


def test_light_time_rounds_up_to_the_export_timestamp_resolution():
    c, a, b = inputs()
    c['one_way_delay'] = {'model': 'constant_assumed', 'seconds': 0.0000011}
    result = assess(c, a, b)
    assert result['contacts'][0]['one_way_delay']['seconds'] == 0.000002


def test_earth_surface_endpoint_does_not_count_as_body_occultation():
    from soma.links import evaluate_geometry
    from soma.terrain.dem import RADIUS_M
    dem, a, b = geometry_inputs()
    common = dict(step_m=2, clearance_m=0.1, body_radius_m=RADIUS_M)
    center = [b['position'][0], b['position'][1]+10, b['position'][2]]
    # The receiver lies on the near surface of this explicitly synthetic body.
    result = evaluate_geometry(dem, a, b, occulting_spheres=[{'id':'test-body', 'center_m':center, 'radius_m':10}], **common)
    assert result['status'] == 'clear'
    ellipsoid = {'id':'test-ellipsoid', 'center_m':center, 'radii_m':[20,10,5], 'rotation_common_to_body':[[1,0,0],[0,1,0],[0,0,1]]}
    result = evaluate_geometry(dem, a, b, occulting_spheres=[], occulting_ellipsoids=[ellipsoid], **common)
    assert result['status'] == 'clear'
    ellipsoid['center_m'][1] -= 5
    result = evaluate_geometry(dem, a, b, occulting_spheres=[], occulting_ellipsoids=[ellipsoid], **common)
    assert result['reason'] == 'test-ellipsoid_ellipsoid_intersection'

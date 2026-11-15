from datetime import timedelta
import copy
import math
import numpy as np
import pytest
from soma.geometry import StateHistory, SyntheticTwoBodyLunarPreset
from soma.time import parse_utc, format_utc


def history_inputs():
    return ({'target':'test-relay','origin':'MOON','frame':'J2000','time_scale':'TDB',
             'position_unit':'km','velocity_unit':'km/s','interpolation':'linear',
             'max_gap_s':20,'coverage':{'start_tdb_s':0,'end_tdb_s':10},
             'provenance_label':'synthetic test state history'},
            [{'epoch':0,'position':[2000,0,0],'velocity':[0,1,0]},
             {'epoch':10,'position':[2000,10,0],'velocity':[0,1,0]}])


def test_state_history_unit_conversion_interpolation_and_coverage():
    metadata, samples = history_inputs()
    history = StateHistory(metadata, samples)
    np.testing.assert_allclose(history.state(5)['position'], [2000000, 5000, 0])
    assert history.state(5)['position_unit'] == 'm'
    assert history.state(5)['epoch_format'] == 'seconds_past_j2000_tdb'
    assert 'linear_position' in history.state(5)['provenance_label']
    samples[0]['position'][0] = 0
    np.testing.assert_allclose(history.state(0)['position'], [2000000, 0, 0])
    with pytest.raises(ValueError, match='coverage'):
        history.state(11)


@pytest.mark.parametrize('field,value', [('origin','EARTH'), ('frame','MOON_ME'), ('velocity_unit','m/s'), ('interpolation','libration_point'), ('max_gap_s',0)])
def test_state_history_rejects_unsupported_conventions(field, value):
    metadata, samples = history_inputs()
    metadata[field] = value
    with pytest.raises(ValueError):
        StateHistory(metadata, samples)


def test_history_does_not_bridge_a_gap_or_duplicate_epoch():
    m, s = history_inputs()
    m['max_gap_s'] = 5
    history = StateHistory(m, s)
    with pytest.raises(ValueError, match='gap'):
        history.state(5)
    s[1]['epoch'] = 0
    with pytest.raises(ValueError, match='increase'):
        StateHistory(m, s)


def test_synthetic_conic_has_hand_calculated_circular_quarter_period():
    # Isolated dynamics test supplies a declared linear test clock. Real UTC
    # conversion is separately exercised with the actual LSK in SPICE tests.
    epoch = '2026-01-01T00:00:00Z'
    start = parse_utc(epoch)
    radius, gm = 2000000, 4.902800066e12
    period = 2*math.pi*math.sqrt(radius**3/gm)
    preset = SyntheticTwoBodyLunarPreset(target='synthetic-relay', epoch_utc=epoch,
        coverage={'start_utc':epoch,'end_utc':'2026-01-02T00:00:00Z'}, gm_m3_s2=gm,
        reference_radius_m=1737400, semimajor_axis_m=radius, eccentricity=0,
        inclination_deg=0, ascending_node_deg=0, argument_periapsis_deg=0, mean_anomaly_deg=0,
        utc_to_et=lambda x:(parse_utc(x)-start).total_seconds())
    np.testing.assert_allclose(preset.state(epoch)['position'], [radius,0,0], atol=1e-8)
    quarter = format_utc(start+timedelta(seconds=period/4))
    np.testing.assert_allclose(preset.state(quarter)['position'], [0,radius,0], atol=.002)
    assert preset.state(quarter)['provenance_label'] == 'synthetic_two_body_lunar_preset'
    assert preset.state(quarter)['frame'] == 'J2000'
    with pytest.raises(ValueError, match='coverage'):
        preset.state('2026-01-03T00:00:00Z')


def test_utc_history_requires_one_kernel_backed_time_layer():
    metadata, samples = history_inputs()
    metadata['time_scale'] = 'UTC'
    metadata['coverage'] = {'start_utc':'2026-01-01T00:00:00Z','end_utc':'2026-01-01T00:00:10Z'}
    samples[0]['epoch'] = metadata['coverage']['start_utc']
    samples[1]['epoch'] = metadata['coverage']['end_utc']
    with pytest.raises(ValueError, match='kernel-backed'):
        StateHistory(metadata, samples)
    history = StateHistory(metadata, samples, utc_to_et=lambda x:(parse_utc(x)-parse_utc(samples[0]['epoch'])).total_seconds())
    assert history.state('2026-01-01T00:00:05Z')['position'] == [2000000,5000,0]
    with pytest.raises(TypeError):
        history.metadata['frame'] = 'IAU_MOON'

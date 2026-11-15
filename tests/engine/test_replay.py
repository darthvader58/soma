"""Replay acceptance and deliberate schedule corruption, independent of MILP."""
from copy import deepcopy
from pathlib import Path
import json
import pytest

from soma.schedule.replay import replay_schedule

ROOT = Path(__file__).resolve().parents[2]


def inputs():
    folder = ROOT/'fixtures'/'synthetic-relay'
    scenario = json.loads((folder/'scenario.json').read_text())
    contacts = json.loads((folder/'contacts.json').read_text())
    allocations = json.loads((folder/'expected.json').read_text())['allocations']
    bins = [{**scenario['analysis_horizon'], 'generation_w': 0, 'power_model': 'piecewise_constant'}]
    return scenario, contacts, allocations, bins


def codes(result):
    return {e['code'] for e in result['errors']}


def test_hand_calculated_relay_and_whole_horizon_base_load():
    result = replay_schedule(*inputs())
    assert result['passed'], result['errors']
    assert result['delivered_bytes'] == 104857600
    assert result['final_byte_arrival_utc'] == '2026-11-14T10:01:23.886080Z'
    expected = 80-(5*4500+20*419.4304)/3600/.9
    assert result['energy_history'][-1]['stored_energy_wh'] == pytest.approx(expected)
    assert result['energy_history'][-1]['epoch_utc'] == '2026-11-14T10:05:00Z'


@pytest.mark.parametrize('mutation,code', [
    ('unknown', 'unknown_contact'), ('duplicate', 'duplicate_bytes'),
    ('early', 'causality'), ('late', 'deadline'), ('small', 'storage_overflow'),
    ('band', 'incompatible_band'), ('bent', 'store_and_forward_required'),
    ('capacity', 'contact_capacity'), ('energy', 'energy_reserve'),
    ('power', 'discharge_power'), ('malformed', 'invalid_allocation'),
    ('generation', 'unknown_inputs'), ('receiver_service', 'service_unavailable'),
    ('radio', 'radio_conflict'), ('fragment', 'causality'),
])
def test_corruption(mutation, code):
    s, c, a, g = inputs()
    if mutation == 'unknown': a[0]['contact_id'] = 'missing'
    elif mutation == 'duplicate':
        copy = deepcopy(a[0]); copy['allocation_id'] = 'other'; copy['chunk_id'] = 'renamed'; a.append(copy)
    elif mutation == 'early': a[1]['source_transmit_interval']['start_utc'] = '2026-11-14T09:01:00Z'
    elif mutation == 'late': s['deadline_utc'] = '2026-11-14T10:00:30Z'
    elif mutation == 'small': s['profiles']['relays'][0]['storage_capacity_bytes'] = 100
    elif mutation == 'band': s['profiles']['relays'][0]['terminals'][0]['band'] = 'other'
    elif mutation == 'bent': s['profiles']['relays'][0]['behavior'] = 'bent_pipe'
    elif mutation == 'capacity': c[1]['available_capacity_bits'] = 100
    elif mutation == 'energy': s['profiles']['hardware'][0]['base_load_w'] = 100
    elif mutation == 'power': s['profiles']['hardware'][0]['battery']['max_discharge_w'] = 10
    elif mutation == 'malformed': a[0]['byte_length'] = None
    elif mutation == 'generation': g[0]['generation_w'] = None
    elif mutation == 'receiver_service':
        c[1]['one_way_delay'] = {'model':'constant_assumed', 'seconds': 600}
        a[0]['receiver_occupancy_interval'] = {'start_utc':'2026-11-14T09:10:00Z','end_utc':'2026-11-14T09:16:59.4304Z'}
        a[0]['byte_available_utc'] = '2026-11-14T09:16:59.4304Z'
    elif mutation == 'radio':
        copy=deepcopy(a[0]); copy['allocation_id']='overlap'; a.append(copy)
    elif mutation == 'fragment': a[1]['chunk_id'] = 'renamed'
    result = replay_schedule(s, c, a, g)
    assert not result['passed']
    assert code in codes(result), result['errors']


def test_unknown_inputs_and_invalid_documents_do_not_throw():
    for args in [({}, [], [], []), (None, None, None, None)]:
        assert not replay_schedule(*args)['passed']


def test_charge_saturates_with_surplus_and_no_simultaneous_discharge():
    s,c,a,g=inputs(); g[0]['generation_w']=1000
    result=replay_schedule(s,c,a,g)
    assert result['passed'], result['errors']
    assert result['energy_history'][-1]['stored_energy_wh']==100


def test_lander_storage_explains_waiting_until_source_transmission_completes():
    scenario, contacts, allocations, generation = inputs()
    result = replay_schedule(scenario, contacts, allocations, generation)
    lander_storage = [value for value in result['storage_intervals'] if value['node_id'] == scenario['lander']['id']]
    assert lander_storage == [{
        'node_id': scenario['lander']['id'], 'chunk_id': allocations[0]['chunk_id'],
        'byte_length': allocations[0]['byte_length'],
        'interval': {'start_utc': scenario['data_ready_utc'], 'end_utc': '2026-11-14T09:06:59.430400Z'},
    }]


def test_only_relay_availability_may_conservatively_delay_physical_availability():
    scenario, contacts, allocations, generation = inputs()
    allocations[0]['byte_available_utc'] = '2026-11-14T09:07:00Z'
    assert replay_schedule(scenario, contacts, allocations, generation)['passed']
    allocations[1]['byte_available_utc'] = '2026-11-14T10:01:24Z'
    result = replay_schedule(scenario, contacts, allocations, generation)
    assert 'earth_availability' in codes(result)
    assert not result['passed']


def test_disabled_propagation_is_not_a_terrain_ephemeris_model():
    scenario, contacts, allocations, generation = inputs()
    scenario['analysis_mode'] = 'terrain_ephemeris'
    result = replay_schedule(scenario, contacts, allocations, generation)
    assert 'disabled_light_time' in codes(result)
    assert not result['passed']

"""Independent arithmetic checks for the plan's invented contact example."""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest


FIXTURES = Path(__file__).resolve().parents[2] / 'fixtures'


def load(family, name):
    return json.loads((FIXTURES / f'synthetic-{family}' / f'{name}.json').read_text())


def epoch(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def seconds(interval):
    delta = epoch(interval['end_utc']) - epoch(interval['start_utc'])
    return Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / 1000000


def test_file_size_and_direct_shortfall():
    for family in ('direct', 'relay'):
        scenario, expected = load(family, 'scenario'), load(family, 'expected')
        assert scenario['data_volume'] == {'value': 100, 'unit': 'MiB'}
        assert 100 * 2**20 == expected['file_bytes'] == 104857600
        assert expected['file_bytes'] * 8 == expected['file_bits'] == 838860800
        direct = load(family, 'contacts')[0]
        capacity = Decimal(direct['payload_rate_bps']) * seconds(direct['source_transmit_window'])
        assert capacity == direct['available_capacity_bits'] == expected['direct_capacity_bits'] == 307200000
        assert expected['file_bits'] - capacity == expected['direct_shortfall_bits'] == 531660800
        assert capacity < expected['file_bits']
        assert expected['energy_feasibility'] == 'not_evaluated'
        assert expected['solver_status'] == 'not_run'
        assert expected['replay_status'] == 'not_implemented'


def test_relay_whole_chunk_timing_and_wait():
    expected = load('relay', 'expected')
    contacts = {c['contact_id']: c for c in load('relay', 'contacts')}
    allocations = expected['allocations']
    for allocation, duration in zip(allocations, ('419.4304', '83.88608'), strict=True):
        contact = contacts[allocation['contact_id']]
        assert allocation['byte_offset'] == 0
        assert allocation['byte_length'] == expected['file_bytes']
        assert Decimal(expected['file_bits']) / contact['payload_rate_bps'] == Decimal(duration)
        assert seconds(allocation['source_transmit_interval']) == Decimal(duration)
        assert allocation['receiver_occupancy_interval'] == allocation['source_transmit_interval']
        assert allocation['byte_available_utc'] == allocation['receiver_occupancy_interval']['end_utc']
        assert epoch(contact['source_transmit_window']['start_utc']) <= epoch(allocation['source_transmit_interval']['start_utc'])
        assert epoch(allocation['source_transmit_interval']['end_utc']) <= epoch(contact['source_transmit_window']['end_utc'])
    assert allocations[0]['chunk_id'] == allocations[1]['chunk_id']
    wait = expected['storage_intervals'][0]
    assert wait['interval']['start_utc'] == allocations[0]['byte_available_utc']
    assert wait['interval']['end_utc'] == allocations[1]['source_transmit_interval']['start_utc']
    assert seconds(wait['interval']) == Decimal('3180.5696')
    assert expected['final_byte_arrival_utc'] == allocations[1]['byte_available_utc']
    assert epoch(expected['final_byte_arrival_utc']) < epoch(load('relay', 'scenario')['deadline_utc'])


def test_controlled_network_change_keeps_task_and_hardware_identical():
    direct, relay = load('direct', 'scenario'), load('relay', 'scenario')
    for field in ('lander', 'data_volume', 'data_ready_utc', 'deadline_utc', 'analysis_horizon', 'hardware_profile_ref'):
        assert direct[field] == relay[field]
    assert direct['profiles']['hardware'] == relay['profiles']['hardware']
    assert direct['profiles']['stations'] == relay['profiles']['stations']
    assert load('direct', 'contacts')[0] == load('relay', 'contacts')[0]
    assert direct['relay_refs'] == []
    assert direct['route_families'] == ['direct_to_earth']
    assert relay['route_families'] == ['direct_to_earth', 'single_lunar_relay']
    assert relay['profiles']['relays'][0]['storage_capacity_bytes'] == 104857600
    assert relay['profiles']['relays'][0]['behavior'] == 'store_and_forward'


@pytest.mark.parametrize('family', ['direct', 'relay'])
def test_contacts_have_explicit_compatible_terminals_and_endpoint_service(family):
    scenario = load(family, 'scenario')
    nodes = {scenario['lander']['id']: scenario['profiles']['hardware'][0]}
    nodes.update({p['id']: p for p in scenario['profiles']['relays'] + scenario['profiles']['stations']})
    for node in nodes.values():
        assert node['storage_capacity_bytes'] >= 104857600
    for contact in load(family, 'contacts'):
        assert contact['one_way_delay'] == {'model': 'disabled_for_synthetic_test', 'seconds': 0}
        terminals = []
        for endpoint in ('sender', 'receiver'):
            node = nodes[contact[endpoint]]
            terminal = next(t for t in node['terminals'] if t['id'] == contact[f'{endpoint}_terminal_id'])
            terminals.append(terminal)
            assert contact['mode_id'] in terminal['mode_ids']
            assert any(epoch(w['start_utc']) <= epoch(contact['source_transmit_window']['start_utc']) and epoch(contact['source_transmit_window']['end_utc']) <= epoch(w['end_utc']) for w in node['service']['windows'])
        assert terminals[0]['band'] == terminals[1]['band']
        assert Decimal(contact['payload_rate_bps']) * seconds(contact['source_transmit_window']) == contact['available_capacity_bits']

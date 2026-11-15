"""Hand-computable and resource perturbation checks of the MILP."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from soma.schedule.optimizer import solve_schedule

ROOT = Path(__file__).resolve().parents[2]


def fixture(name='synthetic-relay'):
    path = ROOT / 'fixtures' / name
    scenario = json.loads((path / 'scenario.json').read_text())
    contacts = json.loads((path / 'contacts.json').read_text())
    generation = [dict(scenario['analysis_horizon'], generation_w=0,
                       power_model='piecewise_constant')]
    return scenario, contacts, generation


def test_direct_insufficient_capacity():
    s,c,g = fixture('synthetic-direct')
    result = solve_schedule(s,c,g,bin_s=10)
    assert result['solver_status'] == 'proven_infeasible_discretized_model'
    assert result['allocations'] == []


def test_relay_100_mib_and_finite_resources():
    s,c,g = fixture()
    result = solve_schedule(s,c,g,bin_s=10,time_limit_s=20)
    assert result['solver_status'] in ('proven_optimum','feasible_incumbent')
    assert result['delivered_bytes'] == 104857600
    assert len(result['allocations']) == 14
    assert min(row['stored_energy_wh'] for row in result['energy_history']) >= 10
    for field,value in [('storage_capacity_bytes',104857599),('behavior','bent_pipe')]:
        altered = deepcopy(s)
        altered['profiles']['relays'][0][field] = value
        failed = solve_schedule(altered,c,g,bin_s=10)
        assert failed['solver_status'] == 'proven_infeasible_discretized_model'


@pytest.mark.parametrize('change',['band','service','power','reserve'])
def test_resource_change_prevents_schedule(change):
    s,c,g = fixture()
    hardware = s['profiles']['hardware'][0]
    if change == 'band':
        s['profiles']['relays'][0]['terminals'][0]['band'] = 'incompatible'
    elif change == 'service':
        s['profiles']['relays'][0]['service']['windows'] = []
    elif change == 'power':
        hardware['battery']['max_discharge_w'] = 10
    else:
        hardware['battery']['reserve_wh'] = 79.9
    result = solve_schedule(s,c,g,bin_s=10)
    assert result['solver_status'] == 'proven_infeasible_discretized_model'


def test_unknown_generation_and_timeout_are_unresolved():
    s,c,g = fixture()
    g[0]['generation_w'] = None
    assert solve_schedule(s,c,g)['solver_status'] == 'unresolved'
    g[0]['generation_w'] = 0
    assert solve_schedule(s,c,g,time_limit_s=0)['solver_status'] == 'unresolved'


def test_delay_and_processing_causality():
    s,c,g = fixture()
    for contact in c:
        contact['one_way_delay'] = {'model':'constant_assumed','seconds':2}
    s['profiles']['relays'][0]['processing_delay_s'] = 3
    result = solve_schedule(s,c,g,bin_s=5,time_limit_s=20)
    assert result['solver_status'] in ('proven_optimum','feasible_incumbent')
    contacts = {row['contact_id']:row for row in c}
    from soma.time import parse_utc
    for chunk in {row['chunk_id'] for row in result['allocations']}:
        hops = sorted((row for row in result['allocations'] if row['chunk_id']==chunk),
                      key=lambda row:row['source_transmit_interval']['start_utc'])
        assert parse_utc(hops[1]['source_transmit_interval']['start_utc']) >= parse_utc(hops[0]['byte_available_utc'])
        for row in hops:
            delay = (parse_utc(row['receiver_occupancy_interval']['end_utc'])-
                     parse_utc(row['source_transmit_interval']['end_utc'])).total_seconds()
            assert delay == contacts[row['contact_id']]['one_way_delay']['seconds']


def tiny():
    s,c,_ = fixture()
    start='2026-11-14T08:50:00Z'; end='2026-11-14T08:50:03Z'
    s['analysis_horizon']={'start_utc':start,'end_utc':end}
    s['data_ready_utc']=start; s['deadline_utc']=end
    s['data_volume']={'value':2,'unit':'byte'}
    for group in s['profiles'].values():
        for profile in group:
            profile['service']['windows']=[dict(s['analysis_horizon'])]
    for contact in c:
        contact['payload_rate_bps']=8
        contact['available_capacity_bits']=16
    return s,c


def test_half_duplex_prevents_simultaneous_relay_receive_transmit():
    s,c=tiny(); s['route_families']=['single_lunar_relay']
    c=c[1:]
    c[0]['source_transmit_window']={'start_utc':'2026-11-14T08:50:00Z','end_utc':'2026-11-14T08:50:02Z'}
    c[1]['source_transmit_window']={'start_utc':'2026-11-14T08:50:01Z','end_utc':'2026-11-14T08:50:03Z'}
    g=[dict(s['analysis_horizon'],generation_w=0,power_model='piecewise_constant')]
    assert solve_schedule(s,c,g,chunk_bytes=1,bin_s=1)['solver_status']=='proven_infeasible_discretized_model'
    s['profiles']['relays'][0]['terminals'][0]['duplex']='full_duplex'
    result=solve_schedule(s,c,g,chunk_bytes=1,bin_s=1)
    assert result['solver_status']=='proven_optimum'
    assert result['final_byte_arrival_utc']=='2026-11-14T08:50:03Z'


def test_instantaneous_power_changes_selected_contact():
    s,c=tiny(); s['route_families']=['direct_to_earth']; s['data_volume']['value']=1
    early=deepcopy(c[0]); late=deepcopy(early)
    early['contact_id']='early';late['contact_id']='late'
    early['source_transmit_window']={'start_utc':'2026-11-14T08:50:00Z','end_utc':'2026-11-14T08:50:01Z'}
    late['source_transmit_window']={'start_utc':'2026-11-14T08:50:02Z','end_utc':'2026-11-14T08:50:03Z'}
    g=[{'start_utc':'2026-11-14T08:50:00Z','end_utc':'2026-11-14T08:50:02Z','generation_w':0,'power_model':'piecewise_constant'},
       {'start_utc':'2026-11-14T08:50:02Z','end_utc':'2026-11-14T08:50:03Z','generation_w':30,'power_model':'piecewise_constant'}]
    unrestricted=solve_schedule(s,[early,late],g,chunk_bytes=1,bin_s=1)
    assert unrestricted['allocations'][0]['contact_id']=='early'
    s['profiles']['hardware'][0]['battery']['max_discharge_w']=10
    constrained=solve_schedule(s,[early,late],g,chunk_bytes=1,bin_s=1)
    assert constrained['allocations'][0]['contact_id']=='late'


def test_huge_dataset_returns_bounded_status_before_chunk_allocation():
    s,c,g = fixture()
    s['data_volume']['value'] = 9007199254740991
    result = solve_schedule(s,c,g,chunk_bytes=1)
    assert result['solver_status'] == 'unresolved'
    assert result['allocations'] == []
    assert 'maximum 32 chunks' in result['warnings'][0]


@pytest.mark.parametrize('kwargs', [
    {'chunk_bytes':True}, {'bin_s':True}, {'time_limit_s':True},
    {'bin_s':float('inf')}, {'time_limit_s':float('nan')},
])
def test_numeric_controls_reject_boolean_and_nonfinite_values(kwargs):
    s,c,g = fixture()
    with pytest.raises(ValueError):
        solve_schedule(s,c,g,**kwargs)


def test_generation_rejects_boolean():
    s,c,g = fixture()
    g[0]['generation_w'] = True
    with pytest.raises(ValueError):
        solve_schedule(s,c,g)


def test_milp_supplies_load_before_charging_or_curtailing():
    s,c=tiny(); s['route_families']=['direct_to_earth']; s['data_volume']['value']=1
    c=c[:1]; c[0]['source_transmit_window']=dict(s['analysis_horizon'])
    battery=s['profiles']['hardware'][0]['battery']
    battery['initial_energy_wh']=battery['capacity_wh']
    g=[dict(s['analysis_horizon'],generation_w=100,power_model='piecewise_constant')]
    result=solve_schedule(s,c,g,chunk_bytes=1,bin_s=1)
    assert result['solver_status']=='proven_optimum'
    for row in result['details']['milp_energy_intervals']:
        assert row['discharge_bus_w']==pytest.approx(0)
        assert row['charge_bus_w']==pytest.approx(0)
        assert row['curtailed_bus_w']==pytest.approx(100-row['electrical_load_w'])
    g[0]['generation_w']=0
    result=solve_schedule(s,c,g,chunk_bytes=1,bin_s=1)
    for row in result['details']['milp_energy_intervals']:
        assert row['charge_bus_w']==pytest.approx(0)
        assert row['curtailed_bus_w']==pytest.approx(0)
        assert row['discharge_bus_w']==pytest.approx(row['electrical_load_w'])

import csv
import hashlib
import io
import json
import zipfile

from soma.engine import plan_delivery
from soma.exports import create_run_package, display_payload
from soma.validation import load_scenario


def test_package_is_stable_and_checksums_cover_every_file():
    scenario = load_scenario('fixtures/synthetic-relay/scenario.json')
    scenario['data_volume'] = {'value': 16, 'unit': 'byte'}
    result = plan_delivery(scenario)
    run = {'scenario': scenario, 'result': result, 'validation': {'valid': True}}
    package = create_run_package(run)
    assert package == create_run_package(run)
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        manifest = json.loads(archive.read('run-manifest.json'))
        assert set(manifest['files']) == set(archive.namelist()) - {'run-manifest.json'}
        for name, record in manifest['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == record['sha256']
        assert json.loads(archive.read('scenario.json')) == scenario
        assert json.loads(archive.read('result.json')) == result
        assert 'empty field' in manifest['csv_unknown_representation']
        rows = list(csv.DictReader(io.StringIO(archive.read('schedule.csv').decode())))
        assert [row['source_transmit_start_utc'] for row in rows] == [a['source_transmit_interval']['start_utc'] for a in result['allocations']]
        assert 'planning model under declared assumptions' in archive.read('explanation.md').decode()
    assert 'position' not in json.dumps(display_payload(run))


def test_unknown_energy_is_blank_never_zero():
    scenario = load_scenario('fixtures/synthetic-direct/scenario.json')
    result = plan_delivery(scenario)
    # A valid implemented unresolved result may preserve an unknown measurement.
    result['model_fidelity'] = 'assumed_rate_simulation'
    result['provenance']['implementation_status'] = 'implemented'
    result['energy_history'] = [{'node_id': scenario['lander']['id'], 'epoch_utc': scenario['data_ready_utc'], 'stored_energy_wh': None}]
    package = create_run_package({'scenario': scenario, 'result': result})
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        row = next(csv.DictReader(io.StringIO(archive.read('energy.csv').decode())))
        assert row['stored_energy_wh'] == ''


def hand_replayed_relay_run():
    """Replay the declared hand fixture independently, without optimizer output."""
    from soma.engine import plan_run
    from soma.schedule.replay import replay_schedule
    from soma.validation import load_json

    scenario = load_scenario('fixtures/synthetic-relay/scenario.json')
    contacts = load_json('fixtures/synthetic-relay/contacts.json')
    allocations = load_json('fixtures/synthetic-relay/expected.json')['allocations']
    generation = [{**scenario['analysis_horizon'], 'generation_w': 0, 'power_model': 'piecewise_constant'}]
    replay = replay_schedule(scenario, contacts, allocations, generation)
    assert replay['passed'], replay['errors']
    run = plan_run(scenario, options={'time_limit_s': 0})
    run['result'].update(status='feasible_under_assumptions', solver_status='feasible_incumbent',
        contacts=contacts, allocations=allocations, storage_intervals=replay['storage_intervals'],
        energy_history=replay['energy_history'], buffer_history=replay['buffer_history'],
        delivered_bytes=replay['delivered_bytes'], final_byte_arrival_utc=replay['final_byte_arrival_utc'])
    run['validation'] = replay
    return run


def test_versioned_summary_uses_replayed_hand_schedule_metrics():
    import pytest
    from soma.exports import summary

    run = hand_replayed_relay_run()
    result = summary(run)
    assert result['artifact_type'] == 'soma_run_summary'
    assert result['format_version'] == '0.4.0'
    assert result['scenario_sha256'] == run['result']['scenario_sha256']
    assert result['route_family'] == 'single_lunar_relay'
    assert result['route_nodes'] == ['synthetic-lander', 'synthetic-lunar-relay', 'synthetic-earth-station']
    assert result['mean_relay_wait_s'] == pytest.approx(3180.5696)
    assert result['lander_communications_energy_wh'] == pytest.approx(20 * 419.4304 / 3600)
    minimum = min(point['stored_energy_wh'] for point in run['validation']['energy_history'])
    assert result['minimum_stored_energy_wh'] == minimum
    assert result['minimum_margin_above_reserve_wh'] == minimum - 10
    assert result['limiting_reason'] == run['result']['provenance']['reason']
    run['result']['status'] = 'unknown'
    for field in ('route_family', 'route_nodes', 'mean_relay_wait_s', 'lander_communications_energy_wh',
                  'minimum_stored_energy_wh', 'minimum_margin_above_reserve_wh'):
        assert summary(run)[field] is None
    run['result']['status'] = 'feasible_under_assumptions'
    run['validation']['passed'] = False
    assert summary(run)['lander_communications_energy_wh'] is None


def test_radio_energy_unions_setup_teardown_per_terminal_direction():
    from copy import deepcopy
    import pytest
    from soma.exports import _lander_radio_energy_wh
    from soma.validation import load_json

    scenario = load_scenario('fixtures/synthetic-relay/scenario.json')
    terminal = scenario['profiles']['hardware'][0]['terminals'][0]
    terminal.update(acquisition_s=2, teardown_s=3)
    contact = load_json('fixtures/synthetic-relay/contacts.json')[1]
    allocations = []
    for start, end in [('2026-11-14T09:00:02Z', '2026-11-14T09:00:12Z'),
                       ('2026-11-14T09:00:10Z', '2026-11-14T09:00:20Z')]:
        allocations.append({'source_transmit_interval': {'start_utc': start, 'end_utc': end}})
    # This unit test exercises interval union only; overlapping records are not
    # offered as a feasible schedule or as evidence that independent replay passed.
    assert _lander_radio_energy_wh(scenario, [(a, contact) for a in allocations]) == pytest.approx(23 * 20 / 3600)
    received = deepcopy(contact)
    received.update(sender='synthetic-lunar-relay', receiver='synthetic-lander', receiver_terminal_id='lander-radio')
    receive = {'receiver_occupancy_interval': {'start_utc': '2026-11-14T09:00:02Z', 'end_utc': '2026-11-14T09:00:12Z'}}
    assert _lander_radio_energy_wh(scenario, [(receive, received)]) == pytest.approx(15 * 5 / 3600)


def test_direct_summary_has_zero_relay_wait_and_manifest_keeps_run_versions():
    from soma.engine import plan_run
    from soma.exports import summary

    scenario = load_scenario('fixtures/synthetic-direct/scenario.json')
    scenario['data_volume'] = {'value': 16, 'unit': 'byte'}
    run = plan_run(scenario, options={'bin_s': 30, 'time_limit_s': 5})
    assert run['validation']['passed']
    result = summary(run)
    assert result['route_family'] == 'direct_to_earth'
    assert result['route_nodes'] == ['synthetic-lander', 'synthetic-earth-station']
    assert result['mean_relay_wait_s'] == 0
    run['details']['software']['versions']['evidence-specific-solver'] = 'test-version'
    with zipfile.ZipFile(io.BytesIO(create_run_package(run))) as archive:
        manifest = json.loads(archive.read('run-manifest.json'))
        assert manifest['software_versions']['evidence-specific-solver'] == 'test-version'
        assert json.loads(archive.read('summary.json')) == summary(run)


def test_display_data_preserves_environment_and_every_selected_epoch():
    from soma.exports import display_data

    run = hand_replayed_relay_run()
    payload = display_data(run)
    assert payload['format_version'] == '0.5.0'
    assert payload['run_version'] == run['scenario']['run_version']
    assert payload['environment'] == run['analysis_inputs']['environment']
    for key in ('contacts', 'allocations', 'storage_intervals', 'energy_history', 'buffer_history'):
        assert payload[key] == run['result'][key]
    assert payload['states'] == []
    assert payload['state_status'] == 'unknown'
    assert 'missing_relay_trajectory:synthetic-lunar-relay' in payload['state_unavailable_reasons']
    assert payload['interpolation'] == 'none_unknown_between_samples'
    epochs = {p['epoch_utc'] for t in payload['environment']['tracks'] for p in t['samples']}
    assert set(payload['sample_epochs_utc']) == epochs
    package = create_run_package(run)
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        assert json.loads(archive.read('display-data.json')) == payload
        assert json.loads(archive.read('renderer-registration.json')) == payload['registration']
    payload['allocations'].clear()
    assert run['result']['allocations']


def test_display_rejects_environment_for_another_scenario():
    import pytest
    from soma.exports import display_data

    run = hand_replayed_relay_run()
    run['analysis_inputs']['environment']['scenario_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='environment scenario hash mismatch'):
        display_data(run)

"""Hosted Earth attitude uses terrestrial geometry and exact registered epochs."""
from copy import deepcopy
from pathlib import Path
import math

import numpy as np
import pytest

from soma.api.delivery import delivery_display, scenario_template


def run_fixture():
    scenario = scenario_template()
    scenario['analysis_horizon']['end_utc'] = '2026-11-24T08:02:00Z'
    scenario['deadline_utc'] = scenario['analysis_horizon']['end_utc']
    allocation = {'allocation_id':'allocation-test','chunk_id':'chunk-0','byte_offset':0,
        'byte_length':1,'contact_id':'contact-test',
        'source_transmit_interval':{'start_utc':'2026-11-24T08:00:10.123Z','end_utc':'2026-11-24T08:00:20.456Z'},
        'receiver_occupancy_interval':{'start_utc':'2026-11-24T08:00:11.234Z','end_utc':'2026-11-24T08:00:21.567Z'},
        'byte_available_utc':'2026-11-24T08:00:21.567Z'}
    return {'scenario':scenario,'analysis_inputs':{'environment':{'analysis_point':deepcopy(scenario['lander'])},
        'states':[{'native_sentinel':'unchanged'}]},'result':{'allocations':[allocation]}}


@pytest.mark.parametrize('allowed', [True,False])
def test_real_spice_earth_rotation_and_wgs84_station_offset(monkeypatch, allowed):
    from soma.validation import load_json
    data_root = Path(__file__).resolve().parents[2]/'api'/'_data'
    if not all((data_root/entry['path']).is_file() for entry in load_json('data/de421-phase2.manifest.json')['kernels']):
        pytest.skip('Matched scientific kernels are acquired separately')
    matrix = [0,1,0,0,-1,0,0,0,0,0,1,0,111,222,333,1]
    registration = {'transform_column_major':matrix if allowed else None,
        'renderer_frame':'test_registered_frame' if allowed else None,
        'release_gate':{'overlays_allowed':allowed}}
    monkeypatch.setattr('soma.exports.display.display_data', lambda run: {'registration':deepcopy(registration)})
    run = run_fixture()
    before = deepcopy(run)
    display = delivery_display(run, data_root=data_root)
    assert run == before
    body = display['earth_body']
    assert body['body_fixed_frame'] == 'ITRF93' and body['reference_ellipsoid'] == 'WGS84'
    assert body['radii_m'] == [6378137,6378137,6356752.314245179]
    if not allowed:
        assert body['status'] == 'unknown' and body['orientation_samples'] == []
        assert display['renderer_states'] == []
        return
    epochs = display['sample_epochs_utc']
    assert [p['epoch_utc'] for p in body['orientation_samples']] == epochs
    assert [s['epoch'] for s in display['renderer_states'] if s['target']=='EARTH'] == epochs
    allocation = run['result']['allocations'][0]
    assert allocation['byte_available_utc'] in epochs
    assert all(value in epochs for key in ('source_transmit_interval','receiver_occupancy_interval') for value in allocation[key].values())
    station = run['scenario']['profiles']['stations'][0]
    latitude, longitude = map(math.radians, (station['latitude_deg'],station['longitude_deg_east']))
    a, _, b = body['radii_m']
    e2 = 1-(b/a)**2
    normal = a/math.sqrt(1-e2*math.sin(latitude)**2)
    expected_offset = np.array([(normal+station['height_m'])*math.cos(latitude)*math.cos(longitude),
        (normal+station['height_m'])*math.cos(latitude)*math.sin(longitude),
        ((1-e2)*normal+station['height_m'])*math.sin(latitude)])
    from soma.geometry import SpiceGeometry
    manifest = load_json('data/de421-phase2.manifest.json')
    manifest['coverage'] = {'start_utc':epochs[0], 'end_utc':epochs[-1]}
    with SpiceGeometry(manifest, data_root) as geometry:
        for sample in body['orientation_samples']:
            epoch = sample['epoch_utc']
            rotation = np.array(sample['rotation_body_fixed_to_renderer_row_major']).reshape(3,3)
            engine_to_renderer = np.array(matrix).reshape(4,4,order='F')[:3,:3]
            expected_rotation = engine_to_renderer @ geometry.spice.pxform('ITRF93','MOON_ME_DE421',geometry._epoch(epoch))
            np.testing.assert_allclose(rotation, expected_rotation, atol=1e-14)
            np.testing.assert_allclose(rotation.T@rotation, np.eye(3), atol=1e-14)
            assert np.linalg.det(rotation) == pytest.approx(1,abs=1e-14)
            records = {record['target']:record for record in display['renderer_states'] if record['epoch']==epoch}
            offset = np.array(records[station['id']]['position'])-records['EARTH']['position']
            np.testing.assert_allclose(rotation.T@offset, expected_offset, atol=1e-6, rtol=0)

"""Reduced display records retain their source samples and schedule epochs."""

from copy import deepcopy

from soma.validation import scenario_sha256


def renderer_registration():
    from soma.geometry.registration import load_renderer_registration
    return load_renderer_registration()


def display_data(run):
    from soma.exports import summary

    scenario, result = run['scenario'], run['result']
    if scenario_sha256(scenario) != result['scenario_sha256']:
        raise ValueError('Display result scenario hash mismatch')
    environment = deepcopy(run.get('analysis_inputs', {}).get('environment'))
    states = deepcopy(run.get('analysis_inputs', {}).get('states', []))
    from soma.validation import validate_documents
    validate_documents(states, 'state')
    for state in states:
        if (state['target'] not in scenario['relay_refs'] or
                (state['frame'], state['origin'], state['time_scale'], state['position_unit']) !=
                ('MOON_ME_DE421', 'MOON', 'UTC', 'm')):
            raise ValueError('Display relay states require enabled targets and Moon-fixed UTC meter samples')
    epochs = set()
    if environment:
        if environment.get('scenario_sha256') != result['scenario_sha256']:
            raise ValueError('Display environment scenario hash mismatch')
        for track in environment.get('tracks', []):
            epochs.update(sample['epoch_utc'] for sample in track.get('samples', []))
        for key in ('solar_samples', 'power_samples'):
            epochs.update(sample['epoch_utc'] for sample in environment.get(key, []))
    epochs.update(state['epoch'] for state in states)
    missing_relays = [node for node in scenario['relay_refs'] if not any(s['target'] == node for s in states)]
    payload = {
        'artifact_type': 'soma_display_payload', 'format_version': '0.5.0',
        'scenario_id': result['scenario_id'], 'scenario_sha256': result['scenario_sha256'],
        'run_version': scenario['run_version'], 'model_fidelity': result['model_fidelity'],
        'registration': renderer_registration(), 'sample_epochs_utc': sorted(epochs),
        'environment': environment, 'states': states, 'state_status': 'stored_samples' if states else 'unknown',
        'state_unavailable_reasons': (["no_stored_trajectory_states"] if not states else []) +
            ['missing_relay_trajectory:' + node for node in missing_relays],
        'interpolation': 'none_unknown_between_samples',
        'summary': summary(run),
    }
    from soma.geometry.registration import load_renderer_conversion, renderer_registration_for_site
    from soma.geometry.surface import SurfacePoint
    resolved = environment.get('analysis_point', scenario['lander']) if environment else scenario['lander']
    for key, value in scenario['lander'].items():
        if key != 'elevation_m' and resolved.get(key) != value:
            raise ValueError('Resolved display point differs from the requested site or equipment heights')
    site=SurfacePoint.from_lander(resolved)
    payload['registration']=renderer_registration_for_site(resolved)
    payload['renderer_conversion']=load_renderer_conversion(payload['registration'])
    matrix = payload['registration'].get('transform_column_major')
    renderer_states = []
    if matrix is not None and payload['registration']['release_gate']['overlays_allowed']:
        for state in states:
            position = state['position']
            transformed = [sum(matrix[column*4+row]*position[column] for column in range(3)) + matrix[12+row]
                           for row in range(3)]
            renderer_states.append({**deepcopy(state), 'position':transformed,
                'source_frame':state['frame'], 'frame':payload['registration']['renderer_frame'],
                'transform_ref':'renderer-registration.json', 'transform_epoch_utc':state['epoch']})
    payload['renderer_states'] = renderer_states
    payload['surface_points']=[{'id':scenario['lander']['id'],'position_m':site.position_m().tolist(),
        'antenna_position_m':site.position_m(site.antenna_height_m).tolist(),
        'panel_position_m':site.position_m(site.panel_height_m).tolist(),
        'frame':payload['registration']['renderer_frame'] or site.frame,'source_frame':site.frame,
        'origin':'MOON','position_unit':'m','epoch':None,'time_scale':'static',
        'elevation_m':site.elevation_m,'antenna_height_m':site.antenna_height_m,'panel_height_m':site.panel_height_m,
        'provenance_label':('Numerical terrain resolved ground elevation; published/interpolated surface quality is retained in the environment provenance. Rendering does not resolve numerical DEM coverage.'
            if scenario['analysis_mode'] == 'terrain_ephemeris' else
            'Declared scenario elevation; synthetic fixtures use an assumed reference-sphere surface. Rendering does not resolve numerical DEM coverage.')}]
    for key in ('contacts', 'allocations', 'storage_intervals', 'energy_history',
                'buffer_history', 'assumptions', 'warnings'):
        payload[key] = deepcopy(result[key])
    return payload

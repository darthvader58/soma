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
    epochs = set()
    if environment:
        if environment.get('scenario_sha256') != result['scenario_sha256']:
            raise ValueError('Display environment scenario hash mismatch')
        for track in environment.get('tracks', []):
            epochs.update(sample['epoch_utc'] for sample in track.get('samples', []))
        for key in ('solar_samples', 'power_samples'):
            epochs.update(sample['epoch_utc'] for sample in environment.get(key, []))
    payload = {
        'artifact_type': 'soma_display_payload', 'format_version': '0.5.0',
        'scenario_id': result['scenario_id'], 'scenario_sha256': result['scenario_sha256'],
        'run_version': scenario['run_version'], 'model_fidelity': result['model_fidelity'],
        'registration': renderer_registration(), 'sample_epochs_utc': sorted(epochs),
        'environment': environment, 'states': [], 'state_status': 'unknown',
        'state_unavailable_reasons': ['no_stored_trajectory_states',
            *['missing_relay_trajectory:' + node for node in scenario['relay_refs']]],
        'interpolation': 'none_unknown_between_samples',
        'summary': summary(run),
    }
    for key in ('contacts', 'allocations', 'storage_intervals', 'energy_history',
                'buffer_history', 'assumptions', 'warnings'):
        payload[key] = deepcopy(result[key])
    return payload

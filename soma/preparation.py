"""Prepare a declared, fixed-coverage synthetic network without hidden defaults."""

from copy import deepcopy
import hashlib
import json

from soma.environment import synthetic_environment_fixture
from soma.time import parse_utc
from soma.validation import load_json, resource_directory, scenario_sha256, validate_document


def prepare_analysis(scenario, *, progress=None, cancel_event=None):
    if scenario['analysis_mode'] == 'terrain_ephemeris':
        from soma.physical import prepare_physical_analysis
        return prepare_physical_analysis(scenario, progress=progress, cancel_event=cancel_event)
    path = resource_directory('data') / 'phase4-synthetic.manifest.json'
    model = load_json(path)
    baseline = model['baseline_scenario']
    failures = []
    if scenario['lander'] != baseline['lander']:
        failures.append('site, frame, elevation or equipment heights differ from the declared synthetic model')
    if any(parse_utc(scenario['analysis_horizon'][k]) != parse_utc(baseline['analysis_horizon'][k]) for k in ('start_utc','end_utc')):
        failures.append('analysis extent differs from the fixed absolute synthetic model horizon')
    if scenario['rate_method'] != 'assumed_net_rate':
        failures.append('the curated model has assumed rates and no complete RF budget inputs')
    for kind, references, fields in (
        ('stations','station_refs',('latitude_deg','longitude_deg_east','height_m','frame','reference_ellipsoid','minimum_elevation_deg')),
        ('relays','relay_refs',('trajectory',)),
    ):
        originals = {p['id']:p for p in baseline['profiles'][kind]}
        actual = {p['id']:p for p in scenario['profiles'][kind]}
        for identifier in scenario[references]:
            if identifier not in originals or any(actual[identifier][k] != originals[identifier][k] for k in fields):
                failures.append(f'{identifier} geometry or trajectory is outside the declared synthetic model')
    if failures:
        return {'format_version':'0.4.0','scenario_sha256':scenario_sha256(scenario),
                'contacts':[], 'generation_bins':[], 'contacts_complete':False, 'generation_complete':False,
                'assumptions':model['assumptions'], 'warnings':failures,
                'provenance':{'model_id':model['id'],'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError('Planning canceled during input preparation')
    if progress:
        progress('horizon_preparation')
    enabled = {scenario['lander']['id'], *scenario['relay_refs'], *scenario['station_refs']}
    lander = scenario['lander']['id']
    templates = [deepcopy(c) for c in model['contact_templates'] if c['sender'] in enabled and c['receiver'] in enabled
                 and ((c['sender'] == lander and c['receiver'] in scenario['station_refs'] and 'direct_to_earth' in scenario['route_families'])
                      or ((c['sender'] in scenario['relay_refs'] or c['receiver'] in scenario['relay_refs']) and 'single_lunar_relay' in scenario['route_families']))]
    if progress:
        progress('contact_construction')
    environment = synthetic_environment_fixture(scenario, templates)
    # The two intentionally blocked/unknown UI examples are not network edges.
    identifiers = {c['contact_id'] for c in templates}
    decisions = [d for d in environment['contact_decisions'] if d['candidate_id'] in identifiers]
    generation = [{'start_utc':a['epoch_utc'], 'end_utc':b['epoch_utc'],
                   'generation_w':a['generated_power_w'], 'power_model':'piecewise_constant'}
                  for a,b in zip(environment['power_samples'],environment['power_samples'][1:])]
    for c in environment['contacts']:
        validate_document(c,'contact')
    return {'format_version':'0.4.0','scenario_sha256':scenario_sha256(scenario),
            'contacts':environment['contacts'], 'generation_bins':generation,
            'contacts_complete':all(d['status'] != 'unknown' for d in decisions),
            'generation_complete':all(b['generation_w'] is not None for b in generation),
            'contact_decisions':decisions, 'environment':environment,
            'assumptions':model['assumptions']+environment['assumptions'], 'warnings':[],
            'provenance':{'model_id':model['id'], 'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                          'source_files':model['source_files'], 'environment':environment['provenance']}}


def checked_analysis_inputs(scenario, inputs):
    inputs = deepcopy(inputs)
    if inputs.get('format_version') != '0.4.0' or inputs.get('scenario_sha256') != scenario_sha256(scenario):
        raise ValueError('Analysis inputs require version 0.4.0 and the exact scenario hash')
    if type(inputs.get('contacts_complete')) is not bool or type(inputs.get('generation_complete')) is not bool:
        raise ValueError('Analysis completeness must be explicitly declared')
    if not isinstance(inputs.get('contacts'),list) or not isinstance(inputs.get('generation_bins'),list):
        raise ValueError('Analysis contacts and generation bins must be arrays')
    if len(inputs['contacts']) > 64 or len(inputs['generation_bins']) > 10000:
        raise ValueError('Analysis input workload exceeds the declared bound')
    identifiers = set()
    for contact in inputs['contacts']:
        validate_document(contact,'contact')
        if contact['contact_id'] in identifiers:
            raise ValueError('Duplicate contact identifier')
        identifiers.add(contact['contact_id'])
    for name in ('assumptions','warnings','provenance'):
        if name not in inputs:
            raise ValueError(f'Analysis inputs omit {name}')
    json.dumps(inputs,allow_nan=False)
    return inputs

"""Authoritative bounded scheduling, gated by an independent schedule replay."""

from copy import deepcopy
from decimal import Decimal, ROUND_CEILING
import hashlib
import math
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

from soma import __version__
from soma.validation import data_volume_bytes, scenario_sha256, validate_document, validate_scenario


def _direct_capacity_upper_bound(scenario, contacts):
    """Optimistic payload bound after readiness and before receiver deadline.

    Ignore radio and energy conflicts, which can only reduce this capacity.
    Keep fractional bits until the final upward rounding so the explanation
    cannot mistake a floating-point underestimate for proven insufficiency.
    """
    from soma.time import parse_utc

    ready = parse_utc(scenario['data_ready_utc'])
    deadline = parse_utc(scenario['deadline_utc'])
    def seconds(delta):
        return Decimal(delta.days*86400+delta.seconds) + Decimal(delta.microseconds)/1000000
    total = Decimal(0)
    for contact in contacts:
        if contact['sender'] != scenario['lander']['id'] or contact['receiver'] not in scenario['station_refs']:
            continue
        start = max(ready, parse_utc(contact['source_transmit_window']['start_utc']))
        duration = min(seconds(parse_utc(contact['source_transmit_window']['end_utc'])-start),
                       seconds(deadline-start)-Decimal(str(contact['one_way_delay']['seconds'])))
        total += min(Decimal(contact['available_capacity_bits']),
                     max(Decimal(0), duration)*Decimal(str(contact['payload_rate_bps'])))
    return int(total.to_integral_value(rounding=ROUND_CEILING))


def _base_result(scenario, *, reason, implemented=False, contacts=()):
    assumed = scenario['rate_method'] == 'assumed_net_rate'
    return {
        'run_version':scenario['run_version'], 'scenario_id':scenario['scenario_id'],
        'scenario_sha256':scenario_sha256(scenario), 'status':'unknown', 'solver_status':'unresolved',
        'model_fidelity':('assumed_rate_simulation' if assumed else 'modeled_link_budget') if implemented else 'not_implemented',
        'assumptions':['Rate method: '+scenario['rate_method'], 'Pointing: '+scenario['pointing_assumption'],
                       'Service: '+scenario['service_assumption_label']],
        'warnings':[], 'contacts':deepcopy(list(contacts)) if implemented else [], 'allocations':[],
        'storage_intervals':[], 'energy_history':[], 'buffer_history':[], 'delivered_bytes':None,
        'final_byte_arrival_utc':None,
        'provenance':{'engine_version':__version__, 'implementation_status':'implemented' if implemented else 'not_implemented',
                      'reason':reason,'kernel_manifest_ref':None,'dataset_manifest_ref':scenario['dataset_manifest_ref'],
                      'source_urls':sorted({url for p in scenario['input_provenance'] for url in p['source_urls']}),
                      'input_provenance':deepcopy(scenario['input_provenance'])},
    }


def _software():
    versions = {'soma':__version__}
    for name in ('pulp','numpy','fastapi','uvicorn'):
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    root = Path(__file__).parent
    sources = {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*.py'))}
    return {'versions':versions, 'source_sha256':sources}


def plan_run(scenario, *, analysis_inputs=None, options=None, progress=None, cancel_event=None):
    """Return detached inputs, native result and independent replay/export evidence.

    The default provider supports a fixed declared synthetic geometry case.
    External analysis inputs are hash-bound; incomplete coverage returns unknown.
    No expected schedule is loaded.
    """
    from soma.preparation import prepare_analysis, checked_analysis_inputs
    from soma.schedule.optimizer import solve_schedule
    from soma.schedule.replay import replay_schedule
    if progress:
        progress('validation')
    scenario = validate_scenario(scenario)
    options = deepcopy(options or {})
    if set(options)-{'chunk_bytes','bin_s','time_limit_s'}:
        raise ValueError('Unsupported scheduler option')
    options = {'chunk_bytes':16777216,'bin_s':5,'time_limit_s':15,**options}
    if type(options['chunk_bytes']) is not int or options['chunk_bytes'] <= 0:
        raise ValueError('chunk_bytes must be a positive integer')
    for name in ('bin_s','time_limit_s'):
        value = options[name]
        if type(value) not in (int,float) or not math.isfinite(value) or value < 0 or (name == 'bin_s' and value == 0):
            raise ValueError(f'{name} must be finite and within its supported range')
    analysis = checked_analysis_inputs(scenario, analysis_inputs) if analysis_inputs is not None else prepare_analysis(scenario, progress=progress, cancel_event=cancel_event)
    complete = analysis['contacts_complete'] and analysis['generation_complete']
    result = _base_result(scenario, reason='Analysis coverage is incomplete; no delivery conclusion is supported.',
                          implemented=complete, contacts=analysis['contacts'])
    result['assumptions'].extend(analysis['assumptions'])
    result['warnings'].extend(analysis['warnings'])
    for decision in analysis.get('contact_decisions', []):
        if decision['status'] != 'usable_under_assumptions':
            result['warnings'].append(f"{decision['candidate_id']}: {decision['status']}: {'; '.join(decision['reasons'])}")
    details = {'policy':'deadline_then_fewer_relay_hops_then_earlier_arrival_then_lower_lander_radio_energy',
               'analysis_provenance':deepcopy(analysis['provenance']), 'software':_software(), 'scheduler_options':options}
    validation = None
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError('Planning canceled before scheduling')
    if complete:
        if progress:
            progress('scheduling')
        solved = solve_schedule(scenario, analysis['contacts'], analysis['generation_bins'], cancel_event=cancel_event, **options)
        details['solver'] = deepcopy(solved['details'])
        result['assumptions'].extend(solved['assumptions'])
        result['warnings'].extend(solved['warnings'])
        status = solved['solver_status']
        if status in ('proven_optimum','feasible_incumbent'):
            if progress:
                progress('replay')
            validation = replay_schedule(scenario, analysis['contacts'], solved['allocations'], analysis['generation_bins'])
            if validation['passed'] and validation['delivered_bytes'] == data_volume_bytes(scenario['data_volume']):
                result.update(status='feasible_under_assumptions', solver_status=status,
                              allocations=solved['allocations'], storage_intervals=validation['storage_intervals'],
                              energy_history=validation['energy_history'], buffer_history=validation['buffer_history'],
                              delivered_bytes=validation['delivered_bytes'], final_byte_arrival_utc=validation['final_byte_arrival_utc'])
                result['provenance']['reason'] = 'The complete dataset schedule passed independent byte, timing, resource and energy replay under the declared assumptions.'
            else:
                result['warnings'].append('Optimizer candidate failed independent replay; no feasible schedule is released.')
                result['provenance']['reason'] = 'Independent replay rejected the optimizer candidate.'
        elif status == 'proven_infeasible_discretized_model':
            result.update(status='infeasible_in_model',solver_status=status,delivered_bytes=0)
            result['provenance']['reason'] = 'The bounded discretized model proved no complete-file schedule under the declared route, storage, radio, service and energy constraints.'
            if set(scenario['route_families']) == {'direct_to_earth'}:
                capacity = _direct_capacity_upper_bound(scenario, analysis['contacts'])
                required = data_volume_bytes(scenario['data_volume'])*8
                if capacity < required:
                    result['provenance']['reason'] = f'Direct contacts after data readiness and before the receiver deadline provide at most {capacity:,} payload bits for a {required:,}-bit file; the complete file cannot fit in the declared network.'
                    details['limiting_bound'] = {'kind':'direct_contact_capacity_upper_bound','available_bits':capacity,'required_bits':required}
        else:
            result['provenance']['reason'] = 'The bounded solver did not establish a complete replayable schedule; infeasibility is unproven.'
    else:
        result['warnings'].append('Missing coverage or unsupported input assumptions remain unknown, not zero or clear.')
    result['warnings'].extend(['Synthetic geometry and assumed service/rates are software-test inputs, not lunar mission predictions.',
                               'This result does not book service or certify navigation, relay operation or thermal survival.',
                               'Scientific map placement depends on the run\'s versioned renderer registration and its tested region; rendered terrain does not resolve numerical coverage.'])
    validate_document(result,'result')
    if progress:
        progress('export')
    return deepcopy({'scenario':scenario, 'result':result, 'analysis_inputs':analysis,
                     'validation':validation, 'details':details})


def plan_delivery(scenario, **kwargs):
    """Plan from standalone inputs; release feasibility only after replay passes."""
    return plan_run(scenario, **kwargs)['result']
